"""Exercise real GCC with its installed default target runtime in QEMU.

The ordinary program jobs contain C source only. One extra scenario adds a
custom archive compiled in a preceding guest job. Programs execute directly
as copies; QEMU compiler diagnostics are not GCC-in-Space execution evidence.
"""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from test_gcc_copy_output import decode
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/gcc'))
from job_format import unpack_job, pack_job
from package_target_library import load_library


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--probes-root', type=Path, required=True)
    parser.add_argument('--qemu', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, root/'run.py')
    image = args.image.resolve()
    manifest = json.loads((image/'image.json').read_text())
    library, receipt = load_library(args.library.resolve())
    assert manifest['target_library']['default'] and manifest['target_library']['units'] == len(receipt['members'])
    assert manifest['target_library']['archive_sha256'] == digest(library) == digest(image/'target-libgcc.a')
    emulator = root/'emulator'
    shutil.copyfile(ROOT/'build/bin/space-256m', emulator)
    emulator.chmod(0o755)
    source = b'unsigned imported(unsigned x) { return x+1; }\n'
    helper = pack_job(['cc1', '--space-result=result.s', '-quiet', '-O2', '-ffreestanding', '-fno-builtin',
                       '-nostdinc', '-o', 'result.s', 'import.c'], {'import.c': source})
    (root/'import.c').write_bytes(source)
    (root/'helper.job').write_bytes(helper)
    command = [sys.executable, str(ROOT/'scripts/gcc/diagnose_guest.py'), '--image', str(image),
               '--job', str(root/'helper.job'), '--qemu', str(args.qemu.resolve()), '--artifacts', str(root/'compiler')]
    (root/'helper-command.json').write_text(json.dumps(command)+'\n')
    subprocess.run(command, check=True)
    assembly = (root/'compiler/result.bin').read_bytes()
    assert b'imported:' in assembly and b'copy.' in assembly
    (root/'imported.s').write_bytes(assembly)
    command = ['ar', 'rcSD', str(root/'user.a'), str(root/'imported.s')]
    (root/'archive-command.json').write_text(json.dumps(command)+'\n')
    subprocess.run(command, capture_output=True, check=True)
    elf = root/'compiler/gcc-diagnostic.elf'
    checks = []
    probes = args.probes_root.resolve()
    candidates = [
        ('multiply', 'gcc-target-library-diagnostic-v2/caller.job', 242406760),
        ('integer', 'gcc-original-libgcc-units-v3/probe/job.bin', 300),
        ('unsigned-to-float', 'gcc-libgcc-floatundi-check-v2/sf/job.bin', 299),
        ('float-to-signed', 'gcc-libgcc-fixdi-check-v1/sf-signed/probe/job.bin', 159),
        ('custom', 'gcc-original-libgcc-units-v3/probe/job.bin', 301),
        ('disabled', 'gcc-original-libgcc-units-v3/probe/job.bin', None),
    ]
    for name, path, expected in candidates:
        argv, files = unpack_job((probes/path).read_bytes())
        argv = [a for a in argv if not a.startswith('--space-library=')]
        assert 'main.c' in files and argv[-1] == 'main.c'
        files = {'main.c': files['main.c']}
        if name == 'custom':
            assert files['main.c'].count(b'return passed;') == 1
            files['main.c'] = b'extern unsigned imported(unsigned);\n'+files['main.c'].replace(
                b'return passed;', b'return imported(passed);')
            argv.insert(argv.index('-quiet'), '--space-library=user.a')
            files['user.a'] = (root/'user.a').read_bytes()
        elif name == 'disabled':
            argv.insert(argv.index('-quiet'), '--space-no-libgcc')
        else:
            assert not any(a.startswith('--space-library=') for a in argv)
            assert set(files) == {'main.c'}
        folder = root/name
        folder.mkdir()
        incoming = pack_job(argv, files)
        (folder/'job.bin').write_bytes(incoming)
        (folder/'main.c').write_bytes(files['main.c'])
        command = [str(args.qemu.resolve()), '-strace', str(elf)]
        (folder/'command.json').write_text(json.dumps(command)+'\n')
        compiled = subprocess.run(command, input=incoming, capture_output=True, timeout=300)
        (folder/'response.bin').write_bytes(compiled.stdout)
        (folder/'syscalls.txt').write_bytes(compiled.stderr)
        status, stdout, stderr, program = decode(compiled.stdout)
        assert status == compiled.returncode
        if expected is None:
            assert status == 126 and not stdout and b'undefined' in stderr and not program
            checks.append({'name': name, 'exit': status, 'job_sha256': digest(folder/'job.bin')})
            print(name, 'expected unresolved runtime without default library', flush=True)
            continue
        assert status == 0 and not stdout and not stderr and len(program) == manifest['copy_program_bytes'], stderr
        (folder/'image.bin').write_bytes(program)
        command = [str(emulator), '--ticks', '10000000', '--core', str(folder/'image.bin'),
                   '--trace-channels', str(folder/'direct.trace')]
        (folder/'direct-command.json').write_text(json.dumps(command)+'\n')
        direct = subprocess.run(command, capture_output=True, timeout=300, check=True)
        (folder/'direct.out').write_bytes(direct.stdout)
        assert not direct.stderr and direct.stdout == struct.pack('<I', expected), (name, direct.stdout)
        assert (folder/'direct.trace').read_bytes().endswith(b' idle\n')
        record = {'name': name, 'direct_result': expected, 'input_files': list(files),
                  'job_sha256': digest(folder/'job.bin'), 'image_sha256': digest(folder/'image.bin')}
        checks.append(record)
        print(name, 'default runtime; direct OUT', expected, flush=True)
    (root/'evidence.json').write_text(json.dumps({'scope': __doc__, 'stream_sha256': manifest['stream_sha256'],
        'library_sha256': receipt['archive_sha256'], 'library_units': len(receipt['members']), 'elf_sha256': digest(elf),
        'qemu_sha256': digest(args.qemu.resolve()), 'emulator_sha256': digest(emulator), 'checks': checks}, indent=2)+'\n')


if __name__ == '__main__':
    main()
