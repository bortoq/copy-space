"""Check ordinary float/double casts to signed/unsigned 64-bit integers.

Original GCC runtime members are linked by the guest linker in QEMU; each
result executes as direct copies. IEEE input bits are decoded with integer
arithmetic for the reference. Every input has a representable truncated result.
"""
import argparse
import hashlib
import json
import random
import shutil
import subprocess
from pathlib import Path

from test_gcc_libgcc_fixuns import run_one
ROOT = Path(__file__).resolve().parents[1]
GROUPS = {
    'fixunsdi': 'gcc-original-libgcc-fixunsdi-v1',
    'fixdi': 'gcc-original-libgcc-fixdi-v1',
    'fixuns': 'gcc-original-libgcc-fixuns-v1',
    'df': 'gcc-original-libgcc-fpdf-v1',
    'sf': 'gcc-original-libgcc-fpsf-v1',
    'usi': 'gcc-original-libgcc-fpcmp-usi-df-v1',
    'dfcmp': 'gcc-original-libgcc-fpcmp-df-v1',
    'sfcmp': 'gcc-original-libgcc-fpcmp-sf-v1',
    'sftodf': 'gcc-original-libgcc-fpconv-sf-v1',
    'integer': 'gcc-original-libgcc-units-v3',
    'bits': 'gcc-original-libgcc-bitops-v3',
}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def truncate(bits, precision, exponent_bits):
    fraction_bits = precision-1
    exponent = (bits >> fraction_bits) & ((1 << exponent_bits)-1)
    significand = bits & ((1 << fraction_bits)-1)
    assert exponent != (1 << exponent_bits)-1
    bias = (1 << (exponent_bits-1))-1
    if exponent:
        significand |= 1 << fraction_bits
    power = (exponent if exponent else 1)-bias-fraction_bits
    integer = significand << power if power >= 0 else significand >> -power
    return -integer if bits >> (fraction_bits+exponent_bits) else integer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--units-root', type=Path, required=True, help='directory containing the producer runs in GROUPS')
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, root/'run.py')
    shutil.copyfile(ROOT/'tests/test_gcc_libgcc_fixuns.py', root/'run-helper.py')
    diagnostic = args.diagnostic.resolve()
    elf = diagnostic/'gcc-diagnostic.elf'
    prior = json.loads((diagnostic/'evidence.json').read_text())
    assert digest(elf) == prior['elf_sha256']
    qemu = Path(json.loads((diagnostic/'command.json').read_text())[0])
    assert digest(qemu) == prior['qemu_sha256']
    emulator = ROOT/'build/bin/space-256m'
    source_hashes = {}
    summary = []
    for mode, precision, exponent_bits, ctype in [('df', 53, 11, 'double'), ('sf', 24, 8, 'float')]:
        for signed in (False, True):
            name = mode+('-signed' if signed else '-unsigned')
            folder = root/name
            folder.mkdir()
            members = [('fixunsdi', 'fixuns'+mode+'di'), ('fixuns', 'fixunsdfsi'), ('usi', 'usi_to_df'),
                ('df', 'mul_df'), ('df', 'addsub_df'), ('dfcmp', 'ge_df'), ('df', 'df_to_si'),
                ('df', 'fpcmp_parts_df'), ('df', 'unpack_df'), ('df', 'pack_df'), ('df', 'thenan_df'),
                ('integer', 'muldi3'), ('bits', 'clzsi2'), ('bits', 'clz')]
            if mode == 'sf':
                members += [('sftodf', 'sf_to_df'), ('sf', 'unpack_sf'), ('df', 'make_df')]
            if signed:
                members += [('fixdi', 'fix'+mode+'di'), (mode+'cmp', 'lt_'+mode)]
                if mode == 'sf':
                    members += [('sf', 'fpcmp_parts_sf')]
            paths = []
            for group, unit in members:
                src = args.units_root.resolve()/GROUPS[group]/unit/'assembly.s'
                record = json.loads((src.parent/'evidence.json').read_text())
                assert record['code'] == record['process_exit'] == 0
                assert digest(src) == record['assembly_sha256'] and src.stat().st_size
                dest = folder/(unit+'.s')
                shutil.copyfile(src, dest)
                paths.append(str(dest))
                source_hashes[str(src)] = digest(src)
            library = folder/'libgcc.a'
            command = ['ar', 'rcSD', str(library)]+paths
            (folder/'archive-command.json').write_text(json.dumps(command)+'\n')
            subprocess.run(command, capture_output=True, check=True)
            bias = (1 << (exponent_bits-1))-1
            fraction_bits = precision-1
            sign_bit = 1 << (fraction_bits+exponent_bits)
            inputs = {0, sign_bit, 1, sign_bit|1, (1 << fraction_bits)-1}
            maximum = (1 << 63)-1 if signed else (1 << 64)-1
            minimum = -(1 << 63) if signed else 0
            for exponent in [bias-2, bias-1, bias, bias+1, bias+23, bias+31, bias+32, bias+52, bias+62, bias+63]:
                for fraction in [0, 1, (1 << fraction_bits)-1]:
                    for sign in ([0, sign_bit] if signed else [0]):
                        bits = sign | exponent << fraction_bits | fraction
                        value = truncate(bits, precision, exponent_bits)
                        if minimum <= value <= maximum:
                            inputs.add(bits)
            rng = random.Random(0xf164+precision+int(signed))
            for _ in range(100):
                exponent = rng.randrange(bias+64)
                bits = exponent << fraction_bits | rng.getrandbits(fraction_bits)
                if signed and rng.getrandbits(1):
                    bits |= sign_bit
                if minimum <= truncate(bits, precision, exponent_bits) <= maximum:
                    inputs.add(bits)
            records = [(bits, truncate(bits, precision, exponent_bits) & ((1 << 64)-1)) for bits in sorted(inputs)]
            assert truncate(bias << fraction_bits, precision, exponent_bits) == 1
            assert truncate(sign_bit | bias << fraction_bits, precision, exponent_bits) == -1
            word = 'u64' if mode == 'df' else 'u32'
            cast = 's64' if signed else 'u64'
            text = ('typedef __UINT64_TYPE__ u64; typedef __INT64_TYPE__ s64; typedef __UINT32_TYPE__ u32;\n'
                'struct record { '+word+' bits; u64 expected; }; static const struct record cases[]={'+
                ','.join('{'+str(bits)+('ULL' if mode == 'df' else 'U')+','+str(expected)+'ULL}' for bits, expected in records)+'};\n'
                'static __attribute__((__noinline__,__noipa__)) u64 convert('+word+' bits){\n'
                'union { '+word+' bits; '+ctype+' value; } input={.bits=bits};\n'
                'return (u64)('+cast+')input.value; }\n'
                'unsigned value(void){unsigned passed=0;for(unsigned i=0;i<'+str(len(records))+';i++)\n'
                'passed+=convert(cases[i].bits)==cases[i].expected;return passed;}\n').encode()
            result = run_one(qemu, elf, emulator, library.read_bytes(), 'libgcc.a', text, folder/'probe', len(records))
            result.update(mode=mode, signed=signed, archive_sha256=digest(library))
            summary.append(result)
            print(name, 'ordinary C casts:', len(records), flush=True)
    (root/'evidence.json').write_text(json.dumps({'scope': __doc__, 'elf_sha256': digest(elf),
        'qemu_sha256': digest(qemu), 'emulator_sha256': digest(emulator),
        'input_assembly_sha256': source_hashes, 'checks': summary}, indent=2)+'\n')


if __name__ == '__main__':
    main()
