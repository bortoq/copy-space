"""Execute separately linked assembly units as primitive copies."""
import argparse
import hashlib
import json
import os
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
    parser.add_argument('--allocate', action='store_true', help='allocate exact rewrite storage inside the linker')
    parser.add_argument('--sanitize', action='store_true')
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
    if args.allocate:
        checks = root/'allocation_checks.c'
        checks.write_text('''#include <stdlib.h>
static unsigned active, calls;
extern void *__real_malloc(size_t);
extern void __real_free(void *);
void *__wrap_malloc(size_t size) {
    const char *fail=getenv("CS_COPY_TEST_ALLOC_FAIL");
    ++calls; if(fail && (unsigned)atoi(fail)==calls) return NULL;
    void *p=__real_malloc(size); if(p) ++active; return p;
}
void __wrap_free(void *p) {
    if(p) { if(!active) abort(); --active; } __real_free(p);
}
__attribute__((destructor)) static void check(void) { if(active) abort(); }
''')
        command[1:1] = ['-DCS_COPY_OBJECT_ALLOC', '-fno-builtin-malloc', str(checks), '-Wl,--wrap=malloc', '-Wl,--wrap=free']
    if args.sanitize:
        command[1:1] = ['-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
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
    caller = b'.global value\nvalue:\ncopy.jsra helper\ncopy.ret\n'
    weak = b'.weak helper\nhelper:\ncopy.inc $r0,10\ncopy.ret\n'
    another = b'.weak helper\nhelper:\ncopy.inc $r0,20\ncopy.ret\n'
    strong = b'.global helper\nhelper:\ncopy.inc $r0,100\ncopy.ret\n'
    alias = weak + b'.global alias\n.set alias,helper\n'
    weak_data = b'.weak shared\n.data\nshared:\n.long 11\n'
    load = b'.global value\nvalue:\ncopy.lda.l $r0,shared\ncopy.ret\n'
    common = b'.comm shared,4,4\n'
    strong_data = b'.global shared\n.data\nshared:\n.long 37\n'
    cases += [([weak, strong, caller], 103), ([strong, weak, caller], 103),
              ([weak, another, caller], 13), ([another, weak, caller], 23),
              ([weak, caller], 13),
              ([weak, b'.global value\nvalue:\ncopy.ldi.l $r2,helper\ncopy.jsr $r2\ncopy.ret\n'], 13),
              ([weak, strong, b'.global value\nvalue:\ncopy.ldi.l $r2,helper\ncopy.jsr $r2\ncopy.ret\n'], 103),
              ([weak + b'.data\n.global pointer\npointer:\n.long helper\n', strong,
                b'.global value\nvalue:\ncopy.lda.l $r2,pointer\ncopy.jsr $r2\ncopy.ret\n'], 103),
              ([alias, strong, b'.global value\nvalue:\ncopy.jsra alias\ncopy.ret\n'], 13),
              ([weak_data, common, load], 0), ([common, weak_data, load], 0),
              ([weak_data, strong_data, load], 37), ([strong_data, weak_data, load], 37),
              ([weak_data + b'.global original\n.set original,shared\n', strong_data,
                b'.global value\nvalue:\ncopy.lda.l $r0,original\ncopy.lda.l $r1,shared\ncopy.add $r0,$r1\ncopy.ret\n'], 48),
              ([b'.weak missing\n.global value\nvalue:\ncopy.ret\n', b'.text\n'], 3),
              ([b'.weak optional\n.global value\nvalue:\ncopy.ldi.l $r0,optional\ncopy.ret\n', b'.weak optional\n'], 0),
              ([b'optional:\ncopy.ret\n', b'.weak optional\n.global value\nvalue:\ncopy.ldi.l $r0,optional\ncopy.ret\n'], 0),
              ([b'.weak optional\n.global value\nvalue:\ncopy.jsra optional\ncopy.ret\n', b'.text\n'], None),
              ([b'.weak optional\n.set alias,optional\n.global value\nvalue:\ncopy.jsra alias\ncopy.ret\n', b'.text\n'], None),
              ([b'.weak optional\n.data\npointer:\n.long optional\n.text\n.global value\nvalue:\ncopy.lda.l $r0,pointer\ncopy.ret\n', b'.weak optional\n.data\npointer:\n.long optional\n'], 0),
              ([b'.weak optional\n.global value\nvalue:\ncopy.ldi.l $r2,optional\ncopy.ldi.l $r3,0\ncopy.cmp $r2,$r3\ncopy.branch.eq .Lnone\ncopy.jsra optional\ncopy.ret\n.Lnone:\ncopy.add $r0,$r1\ncopy.ret\n', b'.text\n'], 7)]
    cases.append(([b'.global value\nvalue:\ncopy.cmp $r0,$r1\ncopy.branch.eq .Lequal\n.Lnext:\ncopy.branch.ltu .Lless\ncopy.ldi.l $r0,9\ncopy.ret\n.Lless:\ncopy.ldi.l $r0,7\ncopy.ret\n.Lequal:\ncopy.ldi.l $r0,1\ncopy.ret\n', b'.text\n'], 7))
    cases += [([b'.weak $r0\n.global value\nvalue:\ncopy.ldi.l $r0,$r0\ncopy.ret\n', b'.text\n'], 0),
              ([b'.weak $r0\n$r0:\ncopy.inc $r0,1\ncopy.ret\n', b'.global $r0\n$r0:\ncopy.inc $r0,2\ncopy.ret\n',
                b'.global value\nvalue:\ncopy.jsra $r0\ncopy.ret\n'], 5)]
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
        assert checked.stdout == (b'' if expected is None else struct.pack('<I', expected)), (index, checked.stdout)
        results.append({'units': len(units), 'result': expected, 'image_sha256': hashlib.sha256(result.stdout).hexdigest()})
    invalid = [
        [b'.global value\nvalue:\ncopy.jsra missing\ncopy.ret\n', b'.text\n'],
        [b'.global value\nvalue:\ncopy.ret\n', b'.global value\nvalue:\ncopy.ret\n'],
        [b'.global value\n.local missing\nvalue:\ncopy.jsra missing\ncopy.ret\n', b'.global missing\nmissing:\ncopy.ret\n'],
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
        [b'.weak optional\n', b'.global value\nvalue:\ncopy.ldi.l $r0,optional\ncopy.ret\n'],
        [b'.weak optional\n.global value\nvalue:\ncopy.ret\n', b'.data\npointer:\n.long optional\n'],
        [b'.weak item\n.comm item,4,4\n.global value\nvalue:\ncopy.ret\n', b'.text\n'],
        [b'.weak helper\n.local helper\nhelper:\ncopy.ret\n', caller],
        [b'.weak helper\nhelper:\ncopy.jsra missing\ncopy.ret\n', strong, caller],
        [b'.global optional\n', b'.weak optional\n.global value\nvalue:\ncopy.ldi.l $r0,optional\ncopy.ret\n'],
        [b'.global value\nvalue:\ncopy.cmp $r0,$r1\ncopy.ret\n', b'.global helper\nhelper:\ncopy.branch.eq .Lhit\ncopy.ret\n.Lhit:\ncopy.ret\n'],
        [b'.weak $r0\n', b'.global value\nvalue:\ncopy.ldi.l $r1,$r0\ncopy.ret\n'],
        [b'.weak $r0\n', b'.global value\nvalue:\ncopy.jsra $r0\ncopy.ret\n'],
        [b'.weak $fp\n', b'.global value\nvalue:\ncopy.lda.l $r0,$fp\ncopy.ret\n'],
    ]
    for index, units in enumerate(invalid):
        incoming = b'\0'.join(units)
        (root / f'invalid-{index}.bin').write_bytes(incoming)
        result = subprocess.run([str(root / 'native')], input=incoming, capture_output=True)
        assert result.returncode == 2 and not result.stdout, index
    # Both units in case 0 contain only external names: rewriting adds just
    # the initial .text line for each unit, plus one final NUL byte.
    needed = sum(map(len, cases[0][0])) + 6 * len(cases[0][0])
    for capacity in (() if args.allocate else (needed, needed + 1)):
        command = native_command[:-2] + [f'-DCS_COPY_OBJECT_TEXT_BYTES={capacity}', '-o', str(root / f'capacity-{capacity}')]
        (root / f'capacity-{capacity}-command.json').write_text(json.dumps(command) + '\n')
        subprocess.run(command, check=True, capture_output=True)
        result = subprocess.run([str(root / f'capacity-{capacity}')], input=b'\0'.join(cases[0][0]), capture_output=True)
        if capacity == needed:
            assert result.returncode == 2 and not result.stdout
        else:
            assert result.returncode == 0 and result.stdout == (root / '0/image.bin').read_bytes()
    if args.allocate:
        for allocation in (1, 2, 3, 4):
            result = subprocess.run([str(root/'native')], input=b'\0'.join(cases[0][0]), capture_output=True,
                env={**os.environ, 'CS_COPY_TEST_ALLOC_FAIL': str(allocation)})
            (root/('allocation-'+str(allocation)+'.stderr')).write_bytes(result.stderr)
            assert result.returncode == 2 and not result.stdout and b'out of memory' in result.stderr
    (root / 'evidence.json').write_text(json.dumps({'scope': 'Separate assembly linking prepared natively; output executed directly as copies. Guest generation not yet verified.',
        'source_sha256': hashes, 'result_space_bytes': args.result_space_bytes, 'direct_cases': results, 'rejected_cases': len(invalid),
        'automatic_scratch': args.allocate, 'allocation_failures_checked': 4 if args.allocate else 0,
        'scratch_exact_fit_bytes': None if args.allocate else needed + 1,
        'scratch_one_byte_short_rejected': not args.allocate}, indent=2) + '\n')
    print('OK separate linking:', len(results), 'programs,', len(invalid), 'rejected inputs')


if __name__ == '__main__':
    main()
