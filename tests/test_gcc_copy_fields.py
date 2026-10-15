"""Check packed fields independently and optionally measure actual guest copies."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/rv32i'))
from build import build
from space_segments import execute_segments


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--emitter', type=Path, default=ROOT / 'runtime/gcc/copy_emit.c')
    parser.add_argument('--guest', action='store_true')
    parser.add_argument('--compiler')
    parser.add_argument('--newlib', type=Path)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    sources = root / 'sources'
    sources.mkdir()
    for path in (args.emitter, ROOT / 'runtime/gcc/copy_emit.h', ROOT / 'tests/fixtures/gcc/copy_fields.c'):
        (sources / path.name).write_bytes(path.read_bytes())
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources.iterdir()}
    cfiles = [sources / 'copy_fields.c', sources / 'copy_emit.c']
    include = '-I' + str(sources)
    command = ['gcc', '-O2', '-Wall', '-Wextra', '-Werror', include] + [str(p) for p in cfiles]
    validation = command + ['-DCS_FIELD_EXHAUSTIVE', '-o', str(root / 'validation')]
    (root / 'validation-command.json').write_text(json.dumps(validation) + '\n')
    subprocess.run(validation, check=True, capture_output=True)
    result = subprocess.run([str(root / 'validation')], capture_output=True, check=True)
    (root / 'validation.out').write_bytes(result.stdout)
    assert result.stdout == b'OK 17408 bit fields and preserved neighbours\n'
    native = command + ['-o', str(root / 'native')]
    (root / 'native-command.json').write_text(json.dumps(native) + '\n')
    subprocess.run(native, check=True, capture_output=True)
    expected = bytearray(b'\xa5' * 64)
    for i in range(64):
        at = (i & 7) + (i >> 3) * 40
        value = 0x9e3779b9 ^ ((i << 24) | (i << 16) | (i << 8) | i)
        for bit in range(1 + (i & 31)):
            byte, shift = (at + bit) // 8, 7 - (at + bit) % 8
            expected[byte] = (expected[byte] & ~(1 << shift)) | (((value >> bit) & 1) << shift)
    result = subprocess.run([str(root / 'native')], capture_output=True, check=True)
    (root / 'native.out').write_bytes(result.stdout)
    assert result.stdout == expected
    evidence = {'source_sha256': hashes, 'field_cases': 17408, 'expected_hex': expected.hex()}
    (root / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    if args.guest:
        if not args.newlib:
            parser.error('--guest requires --newlib')
        prefix = args.newlib.resolve() / 'riscv64-unknown-elf'
        manifest = build(cfiles, root / 'bench.stream', compiler=args.compiler, stream=True,
            memory_bytes=65536, extra_cflags=[include, '-isystem', str(prefix / 'include'),
                '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections'],
            extra_libraries=['-Wl,--start-group', str(prefix / 'lib/libc.a'), '-lgcc', '-Wl,--end-group'])
        execution = execute_segments(ROOT / 'build/bin/space', root / 'space', root / 'bench.stream',
            space_bytes=manifest['space_bytes'], layer_bytes=manifest['layer_bits'] // 8,
            ticks=100000, timeout=300, compression='zstd')
        assert (root / 'space/program.in').read_bytes() == expected
        raw = (root / 'space/space.bin').read_bytes()
        def word(at):
            return sum(((raw[(at+i)//8] >> (7-(at+i)%8)) & 1) << i for i in range(32))
        assert word(132128) == 10 and word(132160) == 0
        evidence['guest_execution'] = execution
        (root / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
        print('OK guest fields:', execution['copy_events'], 'copies', flush=True)
    print(result.stdout.hex() if args.guest else 'OK 17408 bit fields')


if __name__ == '__main__':
    main()
