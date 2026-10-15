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
    args = parser.parse_args()
    if args.qemu and args.resume:
        parser.error('resume is only supported for Space runs')
    image, root = args.image.resolve(), args.artifacts.resolve()
    manifest = json.loads((image/'image.json').read_text())
    assert manifest['target'] == 'copyspace-unknown-elf' and manifest['copy_output']
    assert digest(image/'gcc.stream') == manifest['stream_sha256']
    configuration = {'stream_sha256': manifest['stream_sha256'], 'qemu': str(args.qemu.resolve()) if args.qemu else None}
    root.mkdir(parents=True, exist_ok=args.resume)
    if args.resume:
        assert json.loads((root/'configuration.json').read_text()) == configuration
        assert (root/'helper.c').read_bytes() == HELPER and (root/'main.c').read_bytes() == MAIN
    else:
        shutil.copyfile(__file__, root/'run.py')
        (root/'configuration.json').write_text(json.dumps(configuration, indent=2)+'\n')
        (root/'helper.c').write_bytes(HELPER)
        (root/'main.c').write_bytes(MAIN)
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

    helper_job = pack(['cc1', '--space-result=result.s']+common+['helper.c'], {'helper.c': HELPER})
    assembly = phase('helper', helper_job)
    assert b'copy.' in assembly and b'local:' in assembly and b'imported:' in assembly
    print('Helper C compiled; forwarding its exact assembly bytes to the next guest job', flush=True)
    argv = ['cc1', '--space-program=result.s', '--space-entry=value', '--space-arg=3', '--space-arg=4',
            '--space-memory=65536', '--space-object=lib/imported.s']+common+['main.c']
    main_job = pack(argv, {'main.c': MAIN, 'lib/imported.s': assembly})
    result = phase('caller', main_job, 10)
    assert len(result) == manifest['copy_program_bytes']
    if args.qemu:
        command = [str(ROOT/'build/bin/space-256m'), '--ticks', '100000', '--core',
                   str(root/'caller/result.bin'), '--trace', str(root/'caller/direct.trace')]
        (root/'caller/direct-command.json').write_text(json.dumps(command)+'\n')
        checked = subprocess.run(command, capture_output=True, check=True, timeout=120)
        (root/'caller/direct.out').write_bytes(checked.stdout)
        assert not checked.stderr and checked.stdout == struct.pack('<I', 10)
        assert (root/'caller/direct.trace').read_bytes().endswith(b' idle\n')
    evidence = {'scope': 'QEMU compiler diagnostic and direct copies' if args.qemu else
                'Both C compilations and separate object linking executed inside primitive Space',
        'original_cc1_sha256': manifest['original_cc1_sha256'], 'stream_sha256': manifest['stream_sha256'],
        'helper_source_sha256': digest(root/'helper.c'), 'main_source_sha256': digest(root/'main.c'),
        'helper_job_sha256': digest(root/'helper.job'), 'caller_job_sha256': digest(root/'caller.job'),
        'forwarded_assembly_sha256': hashlib.sha256(assembly).hexdigest(),
        'direct_image_sha256': hashlib.sha256(result).hexdigest(), 'direct_result': 10}
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('OK separate GNU C jobs:', evidence['scope'], '; repeated private local names; result 10', flush=True)


if __name__ == '__main__':
    main()
