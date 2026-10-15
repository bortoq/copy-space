"""Execute separately linked assembly units as primitive copies."""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--result-space-bytes', type=int, choices=[2097152, 268435456], default=2097152)
    parser.add_argument('--assembly', type=Path, action='append', help='also link these real GCC outputs together')
    parser.add_argument('--expected-result', type=lambda s: int(s, 0))
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    paths = [Path('tests/fixtures/gcc/copy_link.c')] + [Path('runtime/gcc') / name for name in ('copy_link.c', 'copy_link.h', 'copy_emit.c', 'copy_emit.h')]
    hashes = {}
    for path in paths:
        target = root / 'sources' / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / path).read_bytes())
        hashes[str(path)] = hashlib.sha256(target.read_bytes()).hexdigest()
    bits = (args.result_space_bytes * 8).bit_length() - 1
    command = ['gcc', '-O2', '-Wall', '-Wextra', '-Werror', '-DCS_COPY_PROGRAM', '-DCS_COPY_OBJECTS',
               '-DCS_COPY_RESULT_ADDRESS_BITS=' + str(bits), '-I' + str(root / 'sources/runtime/gcc')]
    command += [str(root / 'sources' / path) for path in paths if path.suffix == '.c'] + ['-o', str(root / 'native')]
    (root / 'native-command.json').write_text(json.dumps(command) + '\n')
    subprocess.run(command, check=True, capture_output=True)
    native_command = command[:]
    cases = [
        ([b'.global value\nvalue:\ncopy.jsra helper\ncopy.ret\n',
          b'.global helper\nhelper:\ncopy.add $r0,$r1\ncopy.ret\n'], 7),
        ([b'.global value\nvalue:\ncopy.jsra helper\ncopy.jsra external\ncopy.ret\nhelper:\ncopy.inc $r0,1\ncopy.ret\n',
          b'.global external\nexternal:\ncopy.jsra helper\ncopy.ret\nhelper:\ncopy.inc $r0,2\ncopy.ret\n'], 6),
        ([b'.global value\nvalue:\ncopy.cmp $r0,$r1\ncopy.branch.ltu .Lsame\ncopy.inc $r0,100\n.Lsame:\ncopy.inc $r0,1\ncopy.jsra helper\ncopy.ret\n',
          b'.global helper\nhelper:\ncopy.cmp $r0,$r1\ncopy.branch.eq .Lsame\ncopy.inc $r0,100\n.Lsame:\ncopy.inc $r0,2\ncopy.ret\n'], 6),
        ([b'.data\ncounter:\n.long 5\n.text\n.global value\nvalue:\ncopy.lda.l $r0,counter\ncopy.jsra external\ncopy.ret\n',
          b'.data\ncounter:\n.long 9\n.text\n.global external\nexternal:\ncopy.lda.l $r1,counter\ncopy.add $r0,$r1\ncopy.ret\n'], 14),
        ([b'.global value\nvalue:\ncopy.lda.l $r0,shared\ncopy.ret\n',
          b'.global shared\n.data\nshared:\n.long 23\n'], 23),
        ([b'.local counter\n.comm counter,4,4\n.global value\nvalue:\ncopy.ldi.l $r0,13\ncopy.sta.l counter,$r0\ncopy.jsra external\ncopy.lda.l $r0,counter\ncopy.ret\n',
          b'.local counter\n.comm counter,4,4\n.global external\nexternal:\ncopy.ldi.l $r0,29\ncopy.sta.l counter,$r0\ncopy.ret\n'], 13),
        ([b'.comm shared,4,4\n.global value\nvalue:\ncopy.sta.l shared,$r0\ncopy.jsra helper\ncopy.ret\n',
          b'.global helper\nhelper:\ncopy.lda.l $r0,shared\ncopy.inc $r0,2\ncopy.ret\n'], 5),
        ([b'.data\ncallback:\n.long helper\n.text\n.global value\nvalue:\ncopy.lda.l $r2,callback\ncopy.jsr $r2\ncopy.jsra external\ncopy.ret\nhelper:\ncopy.inc $r0,1\ncopy.ret\n',
          b'.global external\nexternal:\ncopy.jsra helper\ncopy.ret\nhelper:\ncopy.inc $r0,2\ncopy.ret\n'], 6),
        ([b'.set alias,helper\n.global value\nvalue:\ncopy.jsra alias\ncopy.jsra external\ncopy.ret\nhelper:\ncopy.inc $r0,1\ncopy.ret\n',
          b'.set alias,helper\n.global external\nexternal:\ncopy.jsra alias\ncopy.ret\nhelper:\ncopy.inc $r0,2\ncopy.ret\n'], 6),
        ([b'.data\nhelper:\n.string "helper # counter"\n.text\n.global value\nvalue:\ncopy.lda.b $r0,helper\ncopy.ret\n', b'.data\nhelper:\n.long 9\n'], 104),
        ([b'.global value\nvalue:\ncopy.ldi.l $r0,0x10000\ncopy.ret\nx10000:\ncopy.ret\n', b'.text\n'], 65536),
        ([b'.data\nunused:\n.long 1\n', b'.global value\nvalue:\ncopy.add $r0,$r1\ncopy.ret\n'], 7),
        ([b'value:\ncopy.add $r0,$r1\ncopy.ret\n'], 7),
        ([b'.global value\nvalue:\ncopy.jsra helper\ncopy.jsra .__cA0.helper\ncopy.ret\nhelper:\ncopy.inc $r0,1\ncopy.ret\n',
          b'.global .__cA0.helper\n.__cA0.helper:\ncopy.inc $r0,4\ncopy.ret\n'], 8),
    ]
    common_pair = [b'.comm shared,4,4\n.global value\nvalue:\ncopy.ldi.l $r0,17\ncopy.sta.l shared,$r0\ncopy.jsra helper\ncopy.ret\n',
                   b'.comm shared,12,32\n.global helper\nhelper:\ncopy.lda.l $r0,shared\ncopy.inc $r0,2\ncopy.ret\n']
    override_pair = [b'.comm shared,12,32\n.global value\nvalue:\ncopy.lda.l $r0,shared\ncopy.ret\n',
                     b'.data\n.global shared\nshared:\n.long 37\n']
    cases += [(common_pair, 19), (common_pair[::-1], 19), (override_pair, 37), (override_pair[::-1], 37),
              ([b'.comm shared,4,4\n.global value\nvalue:\ncopy.ldi.l $r0,after\ncopy.ldi.l $r1,shared\ncopy.sub $r0,$r1\ncopy.ret\n',
                b'.comm shared,12,32\n.comm after,4,4\n'], 12),
              ([b'.data\n.byte 1\n.comm shared,4,4\n.text\n.global value\nvalue:\ncopy.ldi.l $r0,shared\ncopy.ret\n',
                b'.comm shared,12,32\n'], 288),
              ([b'.comm counter,4,4\n.global value\nvalue:\ncopy.ldi.l $r0,counter\ncopy.ret\n',
                b'.data\ncounter:\n.long 9\n'], 260),
              ([b'.comm shared,4,4\n.comm shared,12,32\n.comm after,4,4\n.global value\nvalue:\ncopy.ldi.l $r0,after\ncopy.ldi.l $r1,shared\ncopy.sub $r0,$r1\ncopy.ret\n',
                b'.comm shared,8,4\n'], 8)]
    cases.append(([b'.comm shared,0,1\n.comm shared,12,32\n.comm after,4,4\n.global value\nvalue:\ncopy.ldi.l $r0,after\ncopy.ldi.l $r1,shared\ncopy.sub $r0,$r1\ncopy.ret\n',
                   b'.comm shared,8,4\n'], 12))
    if args.assembly:
        if args.expected_result is None or not 0 <= args.expected_result <= 0xffffffff:
            parser.error('--assembly requires a uint32 --expected-result')
        cases.append(([p.read_bytes() for p in args.assembly], args.expected_result))
    results = []
    emulator = ROOT / 'build/bin' / ('space' if bits == 24 else 'space-256m')
    for index, (units, expected) in enumerate(cases):
        folder = root / str(index)
        folder.mkdir()
        for i, unit in enumerate(units):
            (folder / f'{i}.s').write_bytes(unit)
        incoming = b'\0'.join(units)
        (folder / 'in.bin').write_bytes(incoming)
        result = subprocess.run([str(root / 'native')], input=incoming, capture_output=True)
        assert result.returncode == 0, (index, result.stderr)
        assert len(result.stdout) == 262144
        (folder / 'image.bin').write_bytes(result.stdout)
        command = [str(emulator), '--core', str(folder / 'image.bin'), '--trace', str(folder / 'trace.txt')]
        (folder / 'command.json').write_text(json.dumps(command) + '\n')
        checked = subprocess.run(command, capture_output=True, check=True, timeout=60)
        (folder / 'out.bin').write_bytes(checked.stdout)
        assert checked.stdout == struct.pack('<I', expected), (index, checked.stdout)
        results.append({'units': len(units), 'result': expected, 'image_sha256': hashlib.sha256(result.stdout).hexdigest()})
    invalid = [
        [b'.global value\nvalue:\ncopy.jsra missing\ncopy.ret\n', b'.text\n'],
        [b'.global value\nvalue:\ncopy.ret\n', b'.global value\nvalue:\ncopy.ret\n'],
        [b'.global value\n.local missing\nvalue:\ncopy.jsra missing\ncopy.ret\n', b'.global missing\nmissing:\ncopy.ret\n'],
        [b'.weak missing\n.global value\nvalue:\ncopy.ret\n', b'.text\n'],
        [b'.global value\nvalue:\ncopy.ret\n.pushsection .data\n', b'.popsection\n'],
        [b'.global value,\nvalue:\ncopy.ret\n', b'.text\n'],
        [b'.local value\n.global value\nvalue:\ncopy.ret\n', b'.text\n'],
        [b'value:\ncopy.ret\n', b'.text\n'],
        [b'.text\n'] * 9,
        [b'.comm shared,-1,4\n.global value\nvalue:\ncopy.ret\n', b'.data\n.global shared\nshared:\n.long 1\n'],
        [b'.comm shared,4,3\n.global value\nvalue:\ncopy.ret\n', b'.data\n.global shared\nshared:\n.long 1\n'],
        [b'.comm shared,4,0\n.global value\nvalue:\ncopy.ret\n', b'.text\n'],
        [b'.comm shared,4,4,8\n.global value\nvalue:\ncopy.ret\n', b'.text\n'],
        [b'.comm shared,4294967296,4\n.global value\nvalue:\ncopy.ret\n', b'.text\n'],
    ]
    for index, units in enumerate(invalid):
        incoming = b'\0'.join(units)
        (root / f'invalid-{index}.bin').write_bytes(incoming)
        result = subprocess.run([str(root / 'native')], input=incoming, capture_output=True)
        assert result.returncode == 2 and not result.stdout, index
    # Both units in case 0 contain only external names: rewriting adds just
    # the initial .text line for each unit, plus one final NUL byte.
    needed = sum(map(len, cases[0][0])) + 6 * len(cases[0][0])
    for capacity in (needed, needed + 1):
        command = native_command[:-2] + [f'-DCS_COPY_OBJECT_TEXT_BYTES={capacity}', '-o', str(root / f'capacity-{capacity}')]
        (root / f'capacity-{capacity}-command.json').write_text(json.dumps(command) + '\n')
        subprocess.run(command, check=True, capture_output=True)
        result = subprocess.run([str(root / f'capacity-{capacity}')], input=b'\0'.join(cases[0][0]), capture_output=True)
        if capacity == needed:
            assert result.returncode == 2 and not result.stdout
        else:
            assert result.returncode == 0 and result.stdout == (root / '0/image.bin').read_bytes()
    (root / 'evidence.json').write_text(json.dumps({'scope': 'Separate assembly linking prepared natively; output executed directly as copies. Guest generation not yet verified.',
        'source_sha256': hashes, 'result_space_bytes': args.result_space_bytes, 'direct_cases': results, 'rejected_cases': len(invalid),
        'scratch_exact_fit_bytes': needed + 1, 'scratch_one_byte_short_rejected': True}, indent=2) + '\n')
    print('OK separate linking:', len(results), 'programs,', len(invalid), 'rejected inputs')


if __name__ == '__main__':
    main()
