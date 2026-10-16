"""Check data relocations containing symbol differences, including GNU label tables.

Native/sanitized linkers prepare images; Space executes only direct copies.
An optional unchanged assembly file from real GCC checks its emitted syntax.
This test alone does not prove GCC execution inside Space.
"""
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare_guest(root, evidence, compiler, newlib):
    if not newlib:
        raise ValueError('--newlib is required to prepare guest generation')
    for path, expected in evidence['source_sha256'].items():
        assert hashlib.sha256((root/'sources'/path).read_bytes()).hexdigest() == expected
    sys.path.insert(0, str(ROOT/'scripts/rv32i'))
    from build import build
    paths = list(evidence['source_sha256'])
    command = json.loads((root/'program-command.json').read_text())
    flags = command[1:command.index(str(root/'sources'/paths[0]))]
    prefix = newlib.resolve()/'riscv64-unknown-elf'
    flags += ['-isystem', str(prefix/'include'), '-DCS_RUNTIME_EXTERNAL_MEMORY',
              '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections']
    selected = [case for case in evidence['direct_cases'] if not case['objects']][-1]
    index = selected['case']
    evidence.update(guest_pending=True, guest_expected_image=f'case-{index}-0/image.bin',
        guest_expected_sha256=selected['image_sha256'], guest_expected_value=selected['expected'])
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    build([root/'sources'/path for path in paths if path.endswith('.c')], root/'linker.stream',
        compiler=compiler, stream=True, optimization='-O2', memory_bytes=8388608,
        space_bytes=67108864, extra_cflags=flags,
        extra_libraries=['-Wl,--start-group', str(prefix/'lib/libc.a'), '-lgcc', '-Wl,--end-group'])
    packet = (root/f'case-{index}-0/input.s').read_bytes()
    (root/'in.bin').write_bytes((root/'linker.stream').read_bytes()+packet)
    shutil.copyfile(ROOT/'build/bin/space-64m', root/'emulator')
    (root/'emulator').chmod(0o755)
    evidence.update(guest_input_sha256=hashlib.sha256((root/'in.bin').read_bytes()).hexdigest(),
        guest_emulator_sha256=hashlib.sha256((root/'emulator').read_bytes()).hexdigest())
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')


def finish_guest(root, evidence, resume=False):
    from space_segments import execute_segments
    assert evidence['guest_pending']
    for path, expected in evidence['source_sha256'].items():
        assert hashlib.sha256((root/'sources'/path).read_bytes()).hexdigest() == expected
    assert hashlib.sha256((root/'in.bin').read_bytes()).hexdigest() == evidence['guest_input_sha256']
    assert hashlib.sha256((root/'emulator').read_bytes()).hexdigest() == evidence['guest_emulator_sha256']
    manifest = json.loads((root/'linker.stream.json').read_text())
    execution = execute_segments(root/'emulator', root/'space', root/'in.bin',
        space_bytes=manifest['space_bytes'], layer_bytes=manifest['layer_bits']//8,
        ticks=1000000, timeout=900, channels_only=True, resume=resume)
    expected = root/evidence['guest_expected_image']
    assert hashlib.sha256(expected.read_bytes()).hexdigest() == evidence['guest_expected_sha256']
    assert (root/'space/program.in').read_bytes() == expected.read_bytes()
    raw = (root/'space/space.bin').read_bytes()
    def word(at):
        return sum(((raw[(at+i)//8]>>(7-(at+i)%8))&1)<<i for i in range(32))
    assert (word(132128), word(132160)) == (10, 0)
    direct = [str(ROOT/'build/bin/space-256m'), '--core', str(root/'space/program.in'),
              '--ticks', '1000000', '--trace-channels', str(root/'guest-direct.trace')]
    (root/'guest-direct-command.json').write_text(json.dumps(direct)+'\n')
    ran = subprocess.run(direct, capture_output=True, timeout=120)
    (root/'guest-direct.out').write_bytes(ran.stdout)
    assert ran.returncode == 0 and not ran.stderr and ran.stdout == struct.pack('<I', evidence['guest_expected_value'])
    assert (root/'guest-direct.trace').read_bytes().endswith(b' idle\n')
    evidence.update(guest_pending=False, guest_exit=0, guest_execution=execution,
        guest_image_sha256=hashlib.sha256(expected.read_bytes()).hexdigest())
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('OK symbol differences lowered inside Space: exact native image', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--assembly', type=Path)
    parser.add_argument('--expected', type=lambda s: int(s, 0), default=17)
    parser.add_argument('--guest', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--compiler')
    parser.add_argument('--newlib', type=Path)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    if args.resume:
        assert args.guest
        evidence = json.loads((root/'evidence.json').read_text())
        assert evidence.get('guest_pending', True), 'guest check already completed'
        if not (root/'linker.stream').exists():
            prepare_guest(root, evidence, args.compiler, args.newlib)
        finish_guest(root, evidence, resume=(root/'space/execution.json').exists())
        return
    if args.guest and not args.newlib:
        parser.error('--guest requires --newlib')
    root.mkdir(parents=True, exist_ok=False)
    paths = ['tests/fixtures/gcc/copy_link.c'] + ['runtime/gcc/'+name for name in
             ('copy_link.c', 'copy_link.h', 'copy_emit.c', 'copy_emit.h')]
    for path in paths:
        target = root/'sources'/path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/path, target)
    shutil.copyfile(__file__, root/'run.py')
    flags = ['-O2', '-Wall', '-Wextra', '-Werror', '-DCS_COPY_PROGRAM',
             '-DCS_COPY_RESULT_ADDRESS_BITS=31', '-DCS_COPY_IMAGE_BYTES=4194304',
             '-DCS_COPY_MEMORY_BYTES=65536', '-DCS_COPY_ASSEMBLY_BYTES=131072',
             '-DCS_COPY_LABEL_CAPACITY=256', '-DCS_COPY_JUMP_CAPACITY=1024',
             '-DCS_COPY_CALL_CAPACITY=128', '-DCS_COPY_SYMBOL_CAPACITY=128',
             '-DCS_COPY_RELOCATION_CAPACITY=128', '-DCS_COPY_OBJECT_TEXT_BYTES=262144',
             '-I'+str(root/'sources/runtime/gcc')]
    binaries = {}
    for objects in (False, True):
        for sanitize in (False, True):
            name = ('objects' if objects else 'program')+('-sanitized' if sanitize else '')
            command = ['gcc']+flags+(['-DCS_COPY_OBJECTS'] if objects else [])
            if sanitize:
                command += ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                            '-fno-pie', '-no-pie']
            command += [str(root/'sources'/path) for path in paths if path.endswith('.c')]
            command += ['-o', str(root/name)]
            (root/(name+'-command.json')).write_text(json.dumps(command)+'\n')
            built = subprocess.run(command, capture_output=True)
            (root/(name+'-compile.stderr')).write_bytes(built.stderr)
            assert built.returncode == 0, built.stderr
            binaries[objects, sanitize] = root/name
    data = b'.data\nlow: .byte 0\n.space 8\nhigh: .byte 0\noffset: '
    load = b'\n.text\n.global value\nvalue: copy.lda.l $r0,offset; copy.ret\n'
    cases = []
    for expression, expected in [
            (b'high-(low)', 9), (b'low-high', 0xfffffff7),
            (b'low-(low)', 0), (b'((high)) - ((low)) + 7', 16),
            (b'high-low-17', 0xfffffff8), (b'high-(low)+0xffffffff', 8),
            (b'2b-(1b)', 9)]:
        source = data+b'.long '+expression+load
        if b'2b' in expression:
            source = source.replace(b'low:', b'1:').replace(b'high:', b'2:')
        cases.append(([source], expected))
    for expression, low, high in [
            (b'low-(high)', 0xfffffff7, 0xffffffff),
            (b'high-low', 9, 0),
            (b'low-high+0x100000000', 0xfffffff7, 0),
            (b'high-low-0x100000000', 9, 0xffffffff)]:
        source = data+b'.quad '+expression+load
        cases.append(([source], low))
        cases.append(([source.replace(b'$r0,offset;', b'$r0,offset+4;')], high))
    cases.append(([data+b'.long alias-(low)\n.set alias,high+2'+load], 11))
    # The final code addresses depend on emitted copy layers, not assembly bytes.
    for backward in (False, True):
        source = (b'.data\noffset: .long target-(base)\n.text\n.global value\nvalue:\n'
                  b'copy.ldi.l $r1,base; copy.lda.l $r2,offset; copy.add $r1,$r2; copy.jmp $r1\n')
        first = b'base: copy.ldi.l $r0,99; copy.ret\n'
        second = b'target: copy.ldi.l $r0,23; copy.ret\n'
        cases.append(([source+(second+first if backward else first+second)], 23))
    # Both objects reuse private names; both sides must be rewritten together.
    cases.append(([
        b'.data\n.L0: .space 3\n.L1: .long .L1-(.L0)\n.text\n.global value\n'
        b'value: copy.jsra helper; copy.lda.l $r1,.L1; copy.add $r0,$r1; copy.ret\n',
        b'.data\n.L0: .space 7\n.L1: .long .L1-(.L0)\n.text\n.global helper\n'
        b'helper: copy.lda.l $r0,.L1; copy.ret\n'], 10))
    if args.assembly:
        cases.append(([args.assembly.read_bytes()], args.expected))
    results = []
    for index, (units, expected) in enumerate(cases):
        for objects in (False, True):
            if len(units) > 1 and not objects:
                continue
            folder = root/f'case-{index}-{int(objects)}'
            folder.mkdir()
            packet = b'\0'.join(units) if objects else units[0]
            (folder/'input.s').write_bytes(packet)
            linked = subprocess.run([str(binaries[objects, False])], input=packet, capture_output=True, timeout=30)
            (folder/'link.stderr').write_bytes(linked.stderr)
            assert linked.returncode == 0 and not linked.stderr, (index, linked.stderr)
            sanitized = subprocess.run([str(binaries[objects, True])], input=packet, capture_output=True,
                env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'}, timeout=30)
            assert sanitized.returncode == 0 and not sanitized.stderr and sanitized.stdout == linked.stdout, sanitized.stderr
            (folder/'image.bin').write_bytes(linked.stdout)
            command = [str(ROOT/'build/bin/space-256m'), '--core', str(folder/'image.bin'),
                       '--ticks', '1000000', '--trace-channels', str(folder/'direct.trace')]
            (folder/'direct-command.json').write_text(json.dumps(command)+'\n')
            run = subprocess.run(command, capture_output=True, timeout=120)
            (folder/'out.bin').write_bytes(run.stdout)
            assert run.returncode == 0 and not run.stderr and run.stdout == struct.pack('<I', expected), (index, run)
            assert (folder/'direct.trace').read_bytes().endswith(b' idle\n')
            results.append({'case': index, 'objects': objects, 'expected': expected,
                'image_sha256': hashlib.sha256(linked.stdout).hexdigest()})
    invalid = [b'high-(missing)', b'missing-(low)', b'high-(low', b'high-low)',
               b'high-()', b'high-(low)+missing', b'high-(low)+1junk', b'high-(low)+18446744073709551616',
               b'high-(low)-18446744073709551616', b'high-(low)+', b'high-low-high', b'high+(low)']
    for index, expression in enumerate(invalid):
        packet = data+b'.long '+expression+load
        (root/f'invalid-{index}.s').write_bytes(packet)
        for key, binary in binaries.items():
            failed = subprocess.run([str(binary)], input=packet, capture_output=True,
                env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'}, timeout=30)
            assert failed.returncode == 2 and not failed.stdout, (expression, key, failed.stderr)
            assert b'AddressSanitizer' not in failed.stderr and b'runtime error:' not in failed.stderr, failed.stderr
    evidence = {'scope': __doc__, 'direct_cases': results, 'rejected_expressions': len(invalid),
        'sanitized_exact': True, 'source_sha256': {path: hashlib.sha256((root/'sources'/path).read_bytes()).hexdigest() for path in paths}}
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('OK symbol differences:', len(results), 'direct cases;', len(invalid), 'rejected expressions', flush=True)
    if args.guest:
        prepare_guest(root, evidence, args.compiler, args.newlib)
        finish_guest(root, evidence)


if __name__ == '__main__':
    main()
