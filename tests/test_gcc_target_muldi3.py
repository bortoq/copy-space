"""Check the C multiplication helper against independent Python products.

This native arithmetic check complements the copyspace ABI executions in
test_gcc_linux_units.py --unit string --entry-probe; it is not Space evidence.
"""
import argparse
import ctypes
import hashlib
import json
import random
import shutil
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    source = root/'muldi3.c'
    shutil.copyfile(ROOT/'runtime/gcc/target/muldi3.c', source)
    shutil.copyfile(__file__, root/'run.py')
    command = ['gcc', '-O2', '-std=c11', '-Wall', '-Wextra', '-Werror', '-shared',
               '-fPIC', str(source), '-o', str(root/'muldi3.so')]
    (root/'command.json').write_text(json.dumps(command)+'\n')
    subprocess.run(command, capture_output=True, check=True)
    multiply = ctypes.CDLL(str(root/'muldi3.so')).__muldi3
    multiply.argtypes = [ctypes.c_uint64, ctypes.c_uint64]
    multiply.restype = ctypes.c_uint64
    boundaries = [0, 1, 65535, 65536, 0xffff0000, 0xffffffff, 0x100000000,
                  0x100000001, 0x8000000000000000, 0xffffffffffffffff]
    rng = random.Random(0xC0F1)
    cases = [(a, b) for a in boundaries for b in boundaries]
    cases += [(rng.getrandbits(64), rng.getrandbits(64)) for _ in range(10000)]
    observed, expected = bytearray(), bytearray()
    for a, b in cases:
        value = multiply(a, b)
        product = (a*b) & 0xffffffffffffffff
        assert value == product, (a, b, value, product)
        observed += struct.pack('<QQQ', a, b, value)
        expected += struct.pack('<Q', product)
    (root/'observed.bin').write_bytes(observed)
    (root/'expected.bin').write_bytes(expected)
    (root/'evidence.json').write_text(json.dumps({'scope': __doc__, 'cases': len(cases),
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'observed_sha256': hashlib.sha256(observed).hexdigest(),
        'expected_sha256': hashlib.sha256(expected).hexdigest()}, indent=2)+'\n')
    print('OK native __muldi3:', len(cases), 'independent Python product comparisons')


if __name__ == '__main__':
    main()
