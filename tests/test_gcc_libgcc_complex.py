"""Check ordinary C complex expressions and integer powers using original libgcc.

The actual target compiler and guest linker run in QEMU, followed by direct
copy execution. This is not evidence of GCC running inside Space. The native
oracle compiles the same frozen GCC 12.5 source and headers, disables HWDBL to
select the target's Smith division algorithm, and forbids FP contraction.
Finite values, infinities and signed zeros compare bitwise; NaN payloads and
signs are deliberately unspecified.
"""
import argparse
import ctypes
import hashlib
import json
import random
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from test_gcc_libgcc_fixuns import run_one

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/gcc'))
from job_format import unpack_job
from package_target_library import load_library

UNITS = ('mulsc3', 'muldc3', 'divsc3', 'divdc3', 'powisf2', 'powidf2')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def command(argv, folder, name):
    (folder/(name+'-command.json')).write_text(json.dumps(argv)+'\n')
    result = subprocess.run(argv, capture_output=True, timeout=180)
    (folder/(name+'.stdout')).write_bytes(result.stdout)
    (folder/(name+'.stderr')).write_bytes(result.stderr)
    assert result.returncode == 0, (argv, result.stderr)


def oracle(units, folder):
    objects = []
    receipts = {}
    for unit in UNITS:
        source = units/unit
        record = json.loads((source/'evidence.json').read_text())
        assert record['code'] == record['process_exit'] == 0
        assert digest(source/'job.bin') == record['job_sha256']
        assert digest(source/'assembly.s') == record['assembly_sha256']
        argv, files = unpack_job((source/'job.bin').read_bytes())
        assert '-DL_'+unit in argv and argv[-1] == 'source/libgcc/libgcc2.c'
        assert set(files) == set(record['files_sha256'])
        for name, data in files.items():
            assert hashlib.sha256(data).hexdigest() == record['files_sha256'][name]
            assert (source/'inputs'/name).read_bytes() == data
        # Use the original, independently compiled scalar algorithm as the
        # reference; Python complex division uses different scaling rules.
        includes = [source/'inputs'/p for p in ('generated', 'build', 'target',
                    'source/libgcc', 'source/include', 'source/gcc/ginclude')]
        obj = folder/(unit+'.o')
        flags = ['-nostdinc', '-Dinhibit_libc', '-DIN_GCC', '-DIN_LIBGCC2',
                 '-fbuilding-libgcc', '-fno-stack-protector', '-ffreestanding',
                 '-DLIBGCC2_UNITS_PER_WORD=4', '-U__LIBGCC_HAVE_HWDBL__', '-DL_'+unit]
        command(['gcc', '-c', '-fPIC', '-O2', '-ffp-contract=off',
                 '-fexcess-precision=standard']+flags+['-I'+str(p) for p in includes]+
                [str(source/'inputs/source/libgcc/libgcc2.c'), '-o', str(obj)], folder, unit)
        objects.append(str(obj))
        receipts[unit] = record['assembly_sha256']
    text = 'typedef __UINT32_TYPE__ u32; typedef __UINT64_TYPE__ u64;\n'
    for mode, ctype, word in [('s', 'float', 'u32'), ('d', 'double', 'u64')]:
        text += f'typedef union {{ {word} bits; {ctype} value; }} bits_{mode};\n'
        for op in ('mul', 'div'):
            name = op+mode+'c3'
            text += f'extern _Complex {ctype} __{name}({ctype},{ctype},{ctype},{ctype});\n'
            text += (f'void ref_{name}({word} a,{word} b,{word} c,{word} d,{word} *out){{'
                     f'bits_{mode} x={{a}},y={{b}},z={{c}},w={{d}},r,i;'
                     f'_Complex {ctype} v=__{name}(x.value,y.value,z.value,w.value);'
                     'r.value=__real__ v;i.value=__imag__ v;out[0]=r.bits;out[1]=i.bits;}\n')
        name = 'powi'+mode+'f2'
        text += f'extern {ctype} __{name}({ctype},int);\n'
        text += (f'void ref_{name}({word} a,int n,{word} *out){{'
                 f'bits_{mode} x={{a}},r;r.value=__{name}(x.value,n);*out=r.bits;}}\n')
    (folder/'oracle.c').write_text(text)
    shared = folder/'oracle.so'
    command(['gcc', '-shared', '-fPIC', '-O2', '-ffp-contract=off',
             '-Wl,-Bsymbolic-functions', str(folder/'oracle.c')]+objects+['-o', str(shared)], folder, 'link')
    command(['gcc', '--version'], folder, 'compiler-version')
    return ctypes.CDLL(str(shared)), receipts


def bit_pattern(value, wide):
    return struct.unpack('<Q' if wide else '<I', struct.pack('<d' if wide else '<f', value))[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--units', type=Path, required=True)
    parser.add_argument('--target-library', type=Path, required=True)
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--image', type=Path, help='verify and use the installed library; send only main.c')
    parser.add_argument('--artifacts', type=Path, required=True)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, root/'run.py')
    shutil.copyfile(ROOT/'tests/test_gcc_libgcc_fixuns.py', root/'run-helper.py')
    native, hashes = oracle(args.units.resolve(), root)
    archive, manifest = load_library(args.target_library.resolve())
    library = root/'libgcc.a'
    shutil.copyfile(archive, library)
    members = []
    for unit in UNITS:
        dest = root/(unit+'.s')
        shutil.copyfile(args.units/unit/'assembly.s', dest)
        members.append(str(dest))
    command(['ar', 'rSD', str(library)]+members, root, 'archive')
    diagnostic = args.diagnostic.resolve()
    elf = diagnostic/'gcc-diagnostic.elf'
    prior = json.loads((diagnostic/'evidence.json').read_text())
    qemu = Path(json.loads((diagnostic/'command.json').read_text())[0])
    assert digest(elf) == prior['elf_sha256'] and digest(qemu) == prior['qemu_sha256']
    if args.image:
        image = args.image.resolve()
        prepared = json.loads((image/'image.json').read_text())
        assert digest(image/'gcc-space.elf') == prepared['elf_sha256'] == prior['original_elf_sha256']
        assert prepared['target_library']['archive_sha256'] == manifest['archive_sha256']
        assert digest(library) == manifest['archive_sha256']
    emulator = ROOT/'build/bin/space-256m'
    checks = []
    for wide in (False, True):
        mode, ctype, word, suffix, width = ('d', 'double', 'u64', 'ULL', 64) if wide else ('s', 'float', 'u32', 'U', 32)
        fraction = 52 if wide else 23
        exponent = ((1 << (11 if wide else 8))-1) << fraction
        sign = 1 << (width-1)
        one, two = bit_pattern(1, wide), bit_pattern(2, wide)
        special = [0, sign, 1, sign|1, (1 << fraction)-1, 1 << fraction,
                   one, sign|one, two, exponent-1, sign|(exponent-1),
                   exponent, sign|exponent, exponent|1, exponent|(1 << (fraction-1))]
        rng = random.Random(0xc099+width)
        cases = [(bit_pattern(1, wide), two, bit_pattern(3, wide), bit_pattern(4, wide))]
        cases += [(x, one, two, sign|one) for x in special]
        cases += [(one, two, x, x) for x in special]
        cases += [(special[rng.randrange(len(special))], special[rng.randrange(len(special))],
                   special[rng.randrange(len(special))], special[rng.randrange(len(special))]) for _ in range(30)]
        cases += [tuple(rng.getrandbits(width) for _ in range(4)) for _ in range(60)]
        for op in ('mul', 'div', 'powi'):
            unit = (op+mode+'c3') if op != 'powi' else 'powi'+mode+'f2'
            func = getattr(native, 'ref_'+unit)
            scalar = ctypes.c_uint64 if wide else ctypes.c_uint32
            power = op == 'powi'
            func.argtypes = ([scalar, ctypes.c_int] if power else [scalar]*4)+[ctypes.POINTER(scalar)]
            func.restype = None
            incoming = cases if not power else [(x,n) for x in special for n in (0,1,-1,2,-2,3,31,-31,-2147483648,2147483647)]
            records = []
            for values in incoming:
                output = (scalar*(1 if power else 2))()
                func(*values, output)
                records.append(tuple(values)+tuple(output))
            if not power:
                if op == 'mul':
                    assert records[0][-2:] == tuple(bit_pattern(v, wide) for v in (-5,10))
                else:
                    golden = (scalar*2)()
                    func(one, two, 0, two, golden)
                    assert tuple(golden) == (one, bit_pattern(-0.5, wide))
            else:
                assert records[special.index(one)*10+3][-1] == one
                assert records[special.index(two)*10+4][-1] == bit_pattern(0.25, wide)
            folder = root/unit
            folder.mkdir()
            (folder/'cases.json').write_text(json.dumps(records)+'\n')
            fields = f'{word} a; int n; {word} r;' if power else f'{word} a,b,c,d,r,i;'
            text = ('typedef __UINT32_TYPE__ u32;typedef __UINT64_TYPE__ u64;\n'
                    f'typedef union {{ {word} bits; {ctype} value; }} scalar;\n'
                    f'struct record {{ {fields} }};static const struct record cases[]={{')
            text += ','.join('{'+','.join(str(v)+('' if power and i == 1 else suffix) for i,v in enumerate(row))+'}' for row in records)+'};\n'
            text += (f'static int equal({word} a,{word} b){{const {word} e={exponent}{suffix}, f={(1 << fraction)-1}{suffix};'
                     'return a==b || ((a&e)==e && (b&e)==e && (a&f) && (b&f));}\n')
            if power:
                text += (f'static __attribute__((__noinline__,__noipa__)) {ctype} calculate({ctype} a,int n)'
                         f'{{return __builtin_powi{"" if wide else "f"}(a,n);}}\n'
                         'unsigned value(void){unsigned passed=0;for(unsigned j=0;j<'+str(len(records))+';j++){'
                         'scalar a={cases[j].a},r;r.value=calculate(a.value,cases[j].n);passed+=equal(r.bits,cases[j].r);}return passed;}\n')
            else:
                operator = '*' if op == 'mul' else '/'
                text += (f'static __attribute__((__noinline__,__noipa__)) _Complex {ctype} calculate(_Complex {ctype} a,_Complex {ctype} b)'
                         f'{{return a{operator}b;}}\n'
                         'unsigned value(void){unsigned passed=0;for(unsigned j=0;j<'+str(len(records))+';j++){'
                         'scalar a={cases[j].a},b={cases[j].b},c={cases[j].c},d={cases[j].d},r,i;'
                         f'_Complex {ctype} x,y,z;__real__ x=a.value;__imag__ x=b.value;__real__ y=c.value;__imag__ y=d.value;'
                         'z=calculate(x,y);r.value=__real__ z;i.value=__imag__ z;'
                         'passed+=equal(r.bits,cases[j].r)&&equal(i.bits,cases[j].i);}return passed;}\n')
            result = run_one(qemu, elf, emulator, library.read_bytes(), 'libgcc.a', text.encode(),
                             folder/'probe', len(records), installed=bool(args.image))
            if args.image:
                argv, files = unpack_job((folder/'probe/job.bin').read_bytes())
                assert set(files) == {'main.c'}
                assert not any(a.startswith('--space-library=') for a in argv)
            checks.append(dict(unit=unit, **result))
            print(unit, 'ordinary C cases:', len(records), flush=True)
    (root/'evidence.json').write_text(json.dumps({'scope': __doc__, 'elf_sha256': digest(elf),
        'qemu_sha256': digest(qemu), 'emulator_sha256': digest(emulator),
        'base_archive_sha256': manifest['archive_sha256'], 'archive_sha256': digest(library),
        'oracle_sha256': digest(root/'oracle.so'), 'installed': bool(args.image),
        'stream_sha256': prepared['stream_sha256'] if args.image else None,
        'input_assembly_sha256': hashes, 'checks': checks}, indent=2)+'\n')


if __name__ == '__main__':
    main()
