"""Check GNU C absolute/relative computed goto at O0 and O2.

Native GCC checks the C oracle. Real target GCC and guest linking execute in
QEMU; the resulting images execute only direct copies in Space. The original
C bytes travel through GCCJOB1. This is not GCC-in-Space execution evidence.
"""
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from test_gcc_copy_output import decode
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/gcc'))
from job_format import pack_job


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    args = parser.parse_args()
    image, diagnostic = args.image.resolve(), args.diagnostic.resolve()
    manifest = json.loads((image/'image.json').read_text())
    prior = json.loads((diagnostic/'evidence.json').read_text())
    assert digest(image/'gcc-space.elf') == prior['original_elf_sha256'] == manifest['elf_sha256']
    elf = diagnostic/'gcc-diagnostic.elf'
    command = json.loads((diagnostic/'command.json').read_text())
    assert command[2] == str(elf) and digest(elf) == prior['elf_sha256']
    assert digest(Path(command[0])) == prior['qemu_sha256']
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, root/'run.py')
    shutil.copyfile(ROOT/'tests/fixtures/gcc/computed_goto.c', root/'main.c')
    data = (root/'main.c').read_bytes()
    (root/'driver.c').write_text('extern unsigned value(void); int main(void){return value()!=22;}\n')
    checks = []
    for optimization in ('O0', 'O2'):
        folder = root/optimization
        folder.mkdir()
        native = ['gcc', '-'+optimization, '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                  str(root/'main.c'), str(root/'driver.c'), '-o', str(folder/'native')]
        (folder/'native-command.json').write_text(json.dumps(native)+'\n')
        built = subprocess.run(native, capture_output=True)
        (folder/'native-compile.stderr').write_bytes(built.stderr)
        assert built.returncode == 0, built.stderr
        ran = subprocess.run([str(folder/'native')], capture_output=True)
        assert ran.returncode == 0 and not ran.stdout and not ran.stderr, ran
        flags = ['-quiet', '-'+optimization, '-std=gnu11', '-ffreestanding', '-fno-builtin',
                 '-nostdinc', '-o', 'result.s', 'main.c']
        for name, service in [('assembly', ['--space-result=result.s']),
                              ('program', ['--space-program=result.s', '--space-entry=value', '--space-memory=65536'])]:
            incoming = pack_job(['cc1']+service+flags, {'main.c': data})
            (folder/(name+'.job')).write_bytes(incoming)
            (folder/(name+'-command.json')).write_text(json.dumps(command)+'\n')
            compiled = subprocess.run(command, input=incoming, capture_output=True, timeout=300)
            (folder/(name+'-response.bin')).write_bytes(compiled.stdout)
            (folder/(name+'-syscalls.txt')).write_bytes(compiled.stderr)
            status, out, err, result = decode(compiled.stdout)
            assert compiled.returncode == status == 0 and not out and not err, err
            (folder/(name+'.bin')).write_bytes(result)
        assembly = (folder/'assembly.bin').read_bytes()
        assert re.search(rb'\.long\s+\.L\w+-\(\.L\w+\)', assembly), 'relative table was optimized away'
        assert (folder/'program.bin').stat().st_size == manifest['copy_program_bytes']
        direct = [str(ROOT/'build/bin/space-256m'), '--core', str(folder/'program.bin'),
                  '--ticks', '10000000', '--trace-channels', str(folder/'direct.trace')]
        (folder/'direct-command.json').write_text(json.dumps(direct)+'\n')
        ran = subprocess.run(direct, capture_output=True, timeout=300)
        (folder/'direct.out').write_bytes(ran.stdout)
        (folder/'direct.stderr').write_bytes(ran.stderr)
        assert ran.returncode == 0 and not ran.stderr and ran.stdout == struct.pack('<I', 22), ran
        assert (folder/'direct.trace').read_bytes().endswith(b' idle\n')
        checks.append({'optimization': optimization, 'checks': 22,
            'job_sha256': digest(folder/'program.job'), 'image_sha256': digest(folder/'program.bin')})
        print('OK computed goto', optimization, ': 22 direct checks', flush=True)
    evidence = {'scope': __doc__, 'checks': checks, 'source_sha256': digest(root/'main.c'),
        'compiler_elf_sha256': digest(elf), 'qemu_sha256': prior['qemu_sha256'],
        'image_stream_sha256': manifest['stream_sha256'], 'emulator_sha256': digest(ROOT/'build/bin/space-256m')}
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')


if __name__ == '__main__':
    main()
