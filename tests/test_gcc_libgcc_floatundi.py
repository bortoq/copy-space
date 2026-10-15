"""Check ordinary uint64_t casts to float/double using original GCC libgcc.

QEMU executes the actual target compiler and guest archive linker. Generated
programs execute as direct copies. Integer-only Python rounding supplies the
reference, including ties and cases that would expose double rounding.
"""
import argparse
import hashlib
import json
import random
import shutil
import struct
import subprocess
from pathlib import Path

from test_gcc_linux_units import pack
from test_gcc_copy_output import decode
ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def integer_float_bits(value, precision, exponent_bits):
    if not value:
        return 0
    exponent = value.bit_length()-1
    shift = exponent-(precision-1)
    if shift > 0:
        significand, remainder = divmod(value, 1 << shift)
        halfway = 1 << (shift-1)
        if remainder > halfway or (remainder == halfway and significand & 1):
            significand += 1
        if significand == 1 << precision:
            significand >>= 1
            exponent += 1
    else:
        significand = value << -shift
    bias = (1 << (exponent_bits-1))-1
    return ((exponent+bias) << (precision-1)) | (significand & ((1 << (precision-1))-1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--floatundi-units', type=Path, required=True)
    parser.add_argument('--df-fine', type=Path, required=True)
    parser.add_argument('--usi-df-units', type=Path, required=True)
    parser.add_argument('--int-units', type=Path, required=True)
    parser.add_argument('--bit-units', type=Path, required=True)
    parser.add_argument('--sf-fine', type=Path, required=True)
    parser.add_argument('--df-to-sf-units', type=Path, required=True)
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, root/'run.py')
    diagnostic = args.diagnostic.resolve()
    elf = diagnostic/'gcc-diagnostic.elf'
    prior = json.loads((diagnostic/'evidence.json').read_text())
    assert digest(elf) == prior['elf_sha256']
    qemu = Path(json.loads((diagnostic/'command.json').read_text())[0])
    assert digest(qemu) == prior['qemu_sha256']
    emulator = ROOT/'build/bin/space-256m'
    input_hashes = {}
    summary = []
    for mode, precision, exponent_bits, ctype in [('df', 53, 11, 'double'), ('sf', 24, 8, 'float')]:
        folder = root/mode
        folder.mkdir()
        units = [(args.floatundi_units, 'floatundi'+mode),
                 (args.df_fine, 'addsub_df'), (args.df_fine, 'mul_df'), (args.usi_df_units, 'usi_to_df'),
                 (args.df_fine, 'pack_df'), (args.df_fine, 'unpack_df'), (args.df_fine, 'thenan_df'),
                 (args.int_units, 'muldi3'), (args.bit_units, 'clzsi2'), (args.bit_units, 'clz')]
        if mode == 'sf':
            units += [(args.df_to_sf_units, 'df_to_sf'), (args.sf_fine, 'make_sf'),
                      (args.sf_fine, 'pack_sf'), (args.sf_fine, 'thenan_sf')]
        members = []
        for source, name in units:
            path = source.resolve()/name/'assembly.s'
            record = json.loads((path.parent/'evidence.json').read_text())
            assert record['code'] == record['process_exit'] == 0
            assert digest(path) == record['assembly_sha256'] and path.stat().st_size
            dest = folder/(name+'.s')
            shutil.copyfile(path, dest)
            members.append(str(dest))
            input_hashes[str(path)] = digest(path)
        library = folder/'libgcc.a'
        command = ['ar', 'rcSD', str(library)]+members
        (folder/'archive-command.json').write_text(json.dumps(command)+'\n')
        subprocess.run(command, capture_output=True, check=True)
        rng = random.Random(0xd164)
        values = {0, 1, 2, 127, 65535, (1 << 24)-1, 1 << 24, 1 << 32, (1 << 53)-1, 1 << 53, (1 << 64)-1}
        values.update(rng.getrandbits(64) for _ in range(50))
        for exponent in range(precision, 64):
            shift = exponent-precision+1
            for odd in (0, 1):
                midpoint = (1 << exponent)+(odd << shift)+(1 << (shift-1))
                values.update(x for x in (midpoint-1, midpoint, midpoint+1) if x < 1 << 64)
        records = [(n, integer_float_bits(n, precision, exponent_bits)) for n in sorted(values)]
        if mode == 'df':
            assert all(bits == struct.unpack('<Q', struct.pack('<d', float(n)))[0] for n, bits in records)
            double_rounding = 0
        else:
            assert integer_float_bits(1, 24, 8) == 0x3f800000
            assert integer_float_bits((1 << 64)-1, 24, 8) == 0x5f800000
            double_rounding = sum(bits != struct.unpack('<I', struct.pack('<f', float(n)))[0] for n, bits in records)
            assert double_rounding > 0
        word = 'u64' if mode == 'df' else 'u32'
        text = ('typedef __UINT64_TYPE__ u64; typedef __UINT32_TYPE__ u32;\n'
                'struct record { u64 a,e; }; static const struct record cases[]={'+
                ','.join('{'+str(n)+'ULL,'+str(bits)+'ULL}' for n, bits in records)+'};\n'
                'static __attribute__((__noinline__,__noipa__)) u64 convert(u64 n) {\n'
                'union { '+ctype+' value; '+word+' bits; } result;\n'
                'result.value=('+ctype+')n; return result.bits; }\n'
                'unsigned value(void){unsigned passed=0; for(unsigned i=0;i<'+str(len(records))+';i++)\n'
                'passed+=convert(cases[i].a)==cases[i].e; return passed; }\n').encode()
        (folder/'main.c').write_bytes(text)
        incoming = pack(['cc1', '--space-program=result.s', '--space-entry=value', '--space-memory=65536',
                         '--space-library=libgcc.a', '-quiet', '-O2', '-ffreestanding', '-fno-builtin', '-nostdinc',
                         '-o', 'result.s', 'main.c'], {'main.c': text, 'libgcc.a': library.read_bytes()})
        (folder/'job.bin').write_bytes(incoming)
        command = [str(qemu), '-strace', str(elf)]
        (folder/'command.json').write_text(json.dumps(command)+'\n')
        compiled = subprocess.run(command, input=incoming, capture_output=True, timeout=300)
        (folder/'response.bin').write_bytes(compiled.stdout)
        (folder/'syscalls.txt').write_bytes(compiled.stderr)
        status, stdout, stderr, image = decode(compiled.stdout)
        assert compiled.returncode == status == 0 and not stdout and not stderr and image, (status, stderr)
        (folder/'image.bin').write_bytes(image)
        command = [str(emulator), '--ticks', '10000000', '--core', str(folder/'image.bin'),
                   '--trace-channels', str(folder/'direct.trace')]
        (folder/'direct-command.json').write_text(json.dumps(command)+'\n')
        result = subprocess.run(command, capture_output=True, timeout=300, check=True)
        (folder/'direct.out').write_bytes(result.stdout)
        assert not result.stderr and result.stdout == struct.pack('<I', len(records)), (mode, result.stdout, len(records))
        assert (folder/'direct.trace').read_bytes().endswith(b' idle\n')
        summary.append({'mode': mode, 'cases': len(records), 'double_rounding_counterexamples': double_rounding,
                        'archive_sha256': digest(library), 'job_sha256': digest(folder/'job.bin'),
                        'image_sha256': digest(folder/'image.bin'), 'direct_output_hex': result.stdout.hex()})
        print(mode, 'ordinary C casts checked:', len(records), 'double rounding cases:', double_rounding, flush=True)
    (root/'evidence.json').write_text(json.dumps({'scope': __doc__, 'elf_sha256': digest(elf),
        'qemu_sha256': digest(qemu), 'emulator_sha256': digest(emulator), 'input_assembly_sha256': input_hashes,
        'checks': summary}, indent=2)+'\n')


if __name__ == '__main__':
    main()
