"""Compile many named code/data sections with real target GCC in QEMU.

The C-only program is linked by the guest and executed as direct copies.
QEMU compiler checks are separate from full GCC execution inside Space.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

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
    parser.add_argument('--expect-link-failure', action='store_true', help='prove the old section limit')
    args = parser.parse_args()
    image, diagnostic = args.image.resolve(), args.diagnostic.resolve()
    manifest = json.loads((image/'image.json').read_text())
    prior = json.loads((diagnostic/'evidence.json').read_text())
    assert digest(image/'gcc-space.elf') == manifest['elf_sha256'] == prior['original_elf_sha256']
    elf = diagnostic/'gcc-diagnostic.elf'
    command = json.loads((diagnostic/'command.json').read_text())
    assert command == [command[0], '-strace', str(elf)]
    assert digest(elf) == prior['elf_sha256'] and digest(Path(command[0])) == prior['qemu_sha256']
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, root/'run.py')
    shutil.copyfile(ROOT/'tests/fixtures/gcc/sections.c', root/'sections.c')
    (root/'image.json').write_text(json.dumps(manifest, indent=2)+'\n')
    source = (root/'sections.c').read_bytes()
    expected = 5381
    for i in range(40):
        expected = ((expected*33) ^ ((i*2654435761+7) & 0xffffffff)) & 0xffffffff
    (root/'native-main.c').write_text('extern unsigned value(void);\n'
        f'int main(void){{return value()!={expected}U;}}\n')
    native = ['gcc', '-O2', '-Wall', '-Wextra', '-Werror', str(root/'sections.c'),
              str(root/'native-main.c'), '-o', str(root/'native')]
    (root/'native-command.json').write_text(json.dumps(native)+'\n')
    built = subprocess.run(native, capture_output=True, timeout=60)
    assert built.returncode == 0, built.stderr
    checked = subprocess.run([str(root/'native')], capture_output=True, timeout=10)
    assert checked.returncode == 0 and not checked.stdout and not checked.stderr
    flags = ['-quiet', '-O2', '-ffreestanding', '-fno-builtin', '-nostdinc', '-o', 'result.s', 'sections.c']
    results = {}
    for name, private in [('assembly', ['--space-result=result.s']),
                          ('program', ['--space-program=result.s', '--space-entry=value'])]:
        incoming = pack_job(['cc1']+private+flags, {'sections.c': source})
        (root/(name+'.job')).write_bytes(incoming)
        (root/(name+'-command.json')).write_text(json.dumps(command)+'\n')
        compiled = subprocess.run(command, input=incoming, capture_output=True, timeout=300)
        (root/(name+'-response.bin')).write_bytes(compiled.stdout)
        (root/(name+'-syscalls.txt')).write_bytes(compiled.stderr)
        status, out, err, result = decode(compiled.stdout)
        assert compiled.returncode == status and not out, (name, compiled.returncode, err)
        (root/(name+'.bin')).write_bytes(result)
        (root/(name+'.stderr')).write_bytes(err)
        if name == 'program' and args.expect_link_failure:
            assert status == 126 and not result and b'unsupported section or directive' in err, err
        else:
            assert status == 0 and not err and result, (name, status, err)
        results[name] = {'status': status, 'result_sha256': digest(root/(name+'.bin'))}
    assembly = (root/'assembly.bin').read_bytes()
    for prefix in ('.data.cell', '.init.text.step'):
        names = set(re.findall(rb'(?m)^\s*\.section\s+"?('+re.escape(prefix.encode())+rb'\d+)', assembly))
        assert names == {f'{prefix}{i}'.encode() for i in range(40)}, names
    if args.expect_link_failure:
        message = (root/'program.stderr').read_bytes()
        match = re.search(rb'copy lowering line (\d+): unsupported section or directive', message)
        assert match, message
        lines = assembly.splitlines()
        index = int(match[1])-1
        assert 0 <= index < len(lines)
        failed_section = re.match(rb'\s*\.section\s+"?([^,"\s]+)', lines[index])
        assert failed_section, lines[index]
        previous = {b'.text'}
        for line in lines[:index]:
            section = re.match(rb'\s*\.section\s+"?([^,"\s]+)', line)
            if section:
                previous.add(section[1])
        assert len(previous) == 16 and failed_section[1] not in previous, (previous, lines[index])
        results['program']['failed_section'] = failed_section[1].decode()
    if not args.expect_link_failure:
        assert (root/'program.bin').stat().st_size == manifest['copy_program_bytes']
        direct = [str(ROOT/'build/bin/space-256m'), '--ticks', '10000000', '--core', str(root/'program.bin'),
                  '--trace-channels', str(root/'direct.trace')]
        (root/'direct-command.json').write_text(json.dumps(direct)+'\n')
        checked = subprocess.run(direct, capture_output=True, timeout=300)
        (root/'direct.out').write_bytes(checked.stdout)
        (root/'direct.stderr').write_bytes(checked.stderr)
        assert checked.returncode == 0 and not checked.stderr and checked.stdout == struct.pack('<I', expected)
        assert (root/'direct.trace').read_bytes().endswith(b' idle\n')
    evidence = {'scope': __doc__, 'expected': expected, 'code_sections': 40, 'data_sections': 40,
                'expected_link_failure': args.expect_link_failure, 'source_sha256': digest(root/'sections.c'),
                'job_sha256': digest(root/'program.job'), 'elf_sha256': prior['elf_sha256'],
                'qemu_sha256': prior['qemu_sha256'], 'stream_sha256': manifest['stream_sha256'],
                'results': results}
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('OK real GCC named sections:', 'old link failure' if args.expect_link_failure else f'direct OUT={expected}')


if __name__ == '__main__':
    main()
