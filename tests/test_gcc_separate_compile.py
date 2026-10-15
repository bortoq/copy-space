"""Compile two C units in separate GCC jobs, then link them inside the guest.

Default execution uses primitive Space for both compiler jobs. --qemu is an
explicit diagnostic alternative and never constitutes GCC-in-Space evidence.
"""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from test_gcc_linux_units import pack
from test_gcc_copy_output import decode

ROOT = Path(__file__).resolve().parents[1]
HELPER = (b'static __attribute__((__noinline__,__noipa__)) unsigned local(unsigned a) { return a+2; }\n'
          b'unsigned imported(unsigned a) { return local(a); }\n')
MAIN = (b'extern unsigned imported(unsigned);\n'
        b'static __attribute__((__noinline__,__noipa__)) unsigned local(unsigned a) { return a+1; }\n'
        b'unsigned value(unsigned a,unsigned b) { return local(a)+imported(b); }\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--qemu', type=Path)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--target-library', action='store_true', help='compile and lazily link target __muldi3')
    args = parser.parse_args()
    if args.qemu and args.resume:
        parser.error('resume is only supported for Space runs')
    image, root = args.image.resolve(), args.artifacts.resolve()
    manifest = json.loads((image/'image.json').read_text())
    assert manifest['target'] == 'copyspace-unknown-elf' and manifest['copy_output']
    assert digest(image/'gcc.stream') == manifest['stream_sha256']
    helper_source = (ROOT/'runtime/gcc/target/muldi3.c').read_bytes() if args.target_library else HELPER
    main_source = (b'typedef __UINT32_TYPE__ u32; typedef __UINT64_TYPE__ u64;\n'
        b'union pair { u64 value; struct { u32 low,high; } word; };\n'
        b'u32 value(u32 alo,u32 ahi,u32 blo,u32 bhi) {\n'
        b'union pair a={.word={alo,ahi}}, b={.word={blo,bhi}}, p;\n'
        b'p.value=a.value*b.value; return p.word.low^p.word.high; }\n') if args.target_library else MAIN
    arguments = [0x89abcdef, 0x12345678, 0xfedcba98, 0x76543210] if args.target_library else [3, 4]
    product = ((arguments[1]<<32 | arguments[0])*(arguments[3]<<32 | arguments[2])) & ((1<<64)-1) if args.target_library else 0
    expected = ((product & 0xffffffff) ^ (product >> 32)) if args.target_library else 10
    configuration = {'stream_sha256': manifest['stream_sha256'], 'qemu': str(args.qemu.resolve()) if args.qemu else None}
    if args.target_library:
        configuration['target_library'] = True
    root.mkdir(parents=True, exist_ok=args.resume)
    if args.resume:
        assert json.loads((root/'configuration.json').read_text()) == configuration
        assert (root/'helper.c').read_bytes() == helper_source and (root/'main.c').read_bytes() == main_source
    else:
        shutil.copyfile(__file__, root/'run.py')
        (root/'configuration.json').write_text(json.dumps(configuration, indent=2)+'\n')
        (root/'helper.c').write_bytes(helper_source)
        (root/'main.c').write_bytes(main_source)
    common = ['-quiet', '-O2', '-ffreestanding', '-fno-builtin', '-nostdinc', '-o', 'result.s']

    def phase(name, incoming, expected=None):
        path = root/(name+'.job')
        if path.exists():
            assert path.read_bytes() == incoming, 'changed '+name+' job'
        else:
            path.write_bytes(incoming)
        folder = root/name
        if not args.qemu:
            evidence_file = folder/'evidence.json'
            if not evidence_file.exists():
                command = [sys.executable, str(ROOT/'scripts/gcc/run_job.py'), '--image', str(image),
                           '--job', str(path), '--artifacts', str(folder)]
                if expected is not None:
                    command += ['--expect-result', str(expected)]
                if folder.exists():
                    assert args.resume, 'run already exists; use --resume'
                    command.append('--resume')
                (root/(name+'-command.json')).write_text(json.dumps(command, indent=2)+'\n')
                subprocess.run(command, check=True)
            evidence = json.loads(evidence_file.read_text())
            assert evidence['guest_exit'] == 0 and evidence['guest_status'] == 10
            assert evidence['stream_sha256'] == manifest['stream_sha256']
            assert evidence['job_sha256'] == digest(path)
            assert evidence['original_cc1_sha256'] == manifest['original_cc1_sha256']
            if expected is not None:
                assert evidence['direct_output_hex'] == struct.pack('<I', expected).hex()
            packet = (folder/'space/program.in').read_bytes()
        elif name == 'helper':
            command = [sys.executable, str(ROOT/'scripts/gcc/diagnose_guest.py'), '--image', str(image),
                       '--job', str(path), '--artifacts', str(folder), '--qemu', str(args.qemu.resolve())]
            (root/(name+'-command.json')).write_text(json.dumps(command, indent=2)+'\n')
            subprocess.run(command, check=True)
            packet = (folder/'out.bin').read_bytes()
        else:
            folder.mkdir()
            command = [str(args.qemu.resolve()), '-strace', str(root/'helper/gcc-diagnostic.elf')]
            (root/(name+'-command.json')).write_text(json.dumps(command, indent=2)+'\n')
            result = subprocess.run(command, input=incoming, capture_output=True, timeout=180)
            (folder/'out.bin').write_bytes(result.stdout)
            (folder/'syscalls.txt').write_bytes(result.stderr)
            assert result.returncode == 0
            packet = result.stdout
        status, stdout, stderr, result = decode(packet)
        assert not status and not stdout and not stderr
        (folder/'result.bin').write_bytes(result)
        return result

    helper_job = pack(['cc1', '--space-result=result.s']+common+['helper.c'], {'helper.c': helper_source})
    assembly = phase('helper', helper_job)
    assert b'copy.' in assembly
    if args.target_library:
        assert b'__muldi3:' in assembly and b'copy.jsra __muldi3' not in assembly
    else:
        assert b'local:' in assembly and b'imported:' in assembly
    print('Helper C compiled; forwarding its exact assembly bytes to the next guest job', flush=True)
    if args.target_library:
        # ar only packages guest-generated text; it does not compile or lower code.
        (root/'muldi3.s').write_bytes(assembly)
        library_path = root/'libgcc.a'
        if not library_path.exists():
            command = ['ar', 'rcSD', str(library_path), str(root/'muldi3.s')]
            (root/'archive-command.json').write_text(json.dumps(command)+'\n')
            subprocess.run(command, check=True, capture_output=True)
        assert subprocess.run(['ar', 't', str(library_path)], capture_output=True, check=True).stdout == b'muldi3.s\n'
        assert subprocess.run(['ar', 'p', str(library_path), 'muldi3.s'], capture_output=True, check=True).stdout == assembly
        library = library_path.read_bytes()
        files = {'main.c': main_source, 'lib/libgcc.a': library}
        extra = ['--space-library=lib/libgcc.a']
    else:
        files = {'main.c': main_source, 'lib/imported.s': assembly}
        extra = ['--space-object=lib/imported.s']
    argv = ['cc1', '--space-program=result.s', '--space-entry=value']+[
        '--space-arg='+str(a) for a in arguments]+['--space-memory=65536']+extra+common+['main.c']
    main_job = pack(argv, files)
    result = phase('caller', main_job, expected)
    assert len(result) == manifest['copy_program_bytes']
    if args.qemu and args.target_library:
        # Prove that ordinary multiplication needs the compiler-generated import.
        without_library = pack([a for a in argv if not a.startswith('--space-library=')], files)
        (root/'caller-without-library.job').write_bytes(without_library)
        command = [str(args.qemu.resolve()), str(root/'helper/gcc-diagnostic.elf')]
        (root/'caller-without-library-command.json').write_text(json.dumps(command)+'\n')
        missing = subprocess.run(command, input=without_library, capture_output=True, timeout=180)
        (root/'caller-without-library.response').write_bytes(missing.stdout)
        status, stdout, stderr, image_bytes = decode(missing.stdout)
        assert missing.returncode == status == 126 and not stdout and not image_bytes
        assert b'undefined' in stderr
    if args.qemu:
        command = [str(ROOT/'build/bin/space-256m'), '--ticks', '100000', '--core',
                   str(root/'caller/result.bin'), '--trace', str(root/'caller/direct.trace')]
        (root/'caller/direct-command.json').write_text(json.dumps(command)+'\n')
        checked = subprocess.run(command, capture_output=True, check=True, timeout=120)
        (root/'caller/direct.out').write_bytes(checked.stdout)
        assert not checked.stderr and checked.stdout == struct.pack('<I', expected)
        assert (root/'caller/direct.trace').read_bytes().endswith(b' idle\n')
    evidence = {'scope': 'QEMU compiler diagnostic and direct copies' if args.qemu else
                'Both C compilations and separate object linking executed inside primitive Space',
        'original_cc1_sha256': manifest['original_cc1_sha256'], 'stream_sha256': manifest['stream_sha256'],
        'helper_source_sha256': digest(root/'helper.c'), 'main_source_sha256': digest(root/'main.c'),
        'helper_job_sha256': digest(root/'helper.job'), 'caller_job_sha256': digest(root/'caller.job'),
        'forwarded_assembly_sha256': hashlib.sha256(assembly).hexdigest(),
        'direct_image_sha256': hashlib.sha256(result).hexdigest(), 'direct_result': expected, 'target_library': args.target_library}
    if args.target_library:
        evidence['archive_sha256'] = hashlib.sha256(library).hexdigest()
        if args.qemu:
            evidence['without_library_exit'] = 126
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('OK separate GNU C jobs:', evidence['scope'], '; target library' if args.target_library else '; repeated private local names', '; result', expected, flush=True)


if __name__ == '__main__':
    main()
