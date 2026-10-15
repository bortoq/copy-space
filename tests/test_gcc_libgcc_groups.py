"""Link original libgcc helper groups into archives and execute direct copies.

The units themselves are compiled by tests/test_gcc_libgcc_units.py; this
test takes such a units directory, packs selected assemblies into an ar
archive, compiles a C harness calling the helpers with the actual copyspace
cc1 in QEMU (GCCJOB1 carries the original bytes), and executes the resulting
Space program with direct copies, checking every result against an
independent Python reference.

Guest archive linking caps selected units at twelve including the explicit
object (runtime/gcc/copy_link.h), hence the helpers ride in small groups:
shifts (six ops), bitops (clz/ctz/clrsb plus the clz table, seven members),
ffs-a (ffs/popcount plus the clz table, five members) and ffs-b
(parity/bswap, four members). Zero-input ctz semantics are target-specific
quirks derived from the compiled copy assembly: __ctzsi2(0) is -1 and
__ctzdi2(0) is 31 (__builtin_ctz(0) is undefined in portable C).

QEMU execution here is a diagnostic only; Space execution of GCC itself
is tracked by the integrated runs, not proven by this test.
"""
import argparse
import hashlib
import json
import random
import struct
import subprocess
import sys
import tarfile
from pathlib import Path

from test_gcc_linux_units import pack
from test_gcc_copy_output import decode
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/gcc'))
from fetch import VERSION, NAME, SHA512


def digest(path, algorithm='sha256'):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def bswap32(a):
    return int.from_bytes((a & 0xffffffff).to_bytes(4, 'little'), 'big')


def bswap64(a):
    return int.from_bytes((a & 0xffffffffffffffff).to_bytes(8, 'little'), 'big')


def ctz32(a):
    a &= 0xffffffff
    return 0xffffffff if a == 0 else (a & -a).bit_length() - 1


def ctz64(a):
    a &= 0xffffffffffffffff
    return 31 if a == 0 else (a & -a).bit_length() - 1


def clz32(a):
    a &= 0xffffffff
    return 32 if a == 0 else 32 - a.bit_length()


def clz64(a):
    a &= 0xffffffffffffffff
    return 64 if a == 0 else 64 - a.bit_length()


def clrsb32(a):
    a &= 0xffffffff
    word = (~a & 0xffffffff) if a >= 0x80000000 else a
    return 31 if word == 0 else clz32(word)-1


def clrsb64(a):
    a &= 0xffffffffffffffff
    hi, lo = (a >> 32) & 0xffffffff, a & 0xffffffff
    if hi == 0:
        word, add = lo, 32
    elif hi == 0xffffffff:
        word, add = ~lo & 0xffffffff, 32
    elif hi < 0x80000000:
        word, add = hi, 0
    else:
        word, add = ~hi & 0xffffffff, 0
    return (32 if word == 0 else clz32(word))+add-1


GROUPS = {
    'shifts': {
        'members': ('ashldi3', 'lshrdi3', 'ashrdi3', 'cmpdi2', 'ucmpdi2', 'negdi2'),
        'decls': ('u64 __ashldi3(u64,int); u64 __lshrdi3(u64,int); u64 __ashrdi3(u64,int);\n'
                  'int __cmpdi2(s64,s64); int __ucmpdi2(u64,u64); u64 __negdi2(u64);\n'),
        'calcs': ('c0', 'c1', 'c2', 'c3', 'c4', 'c5'),
        'fns': ('static __attribute__((__noinline__,__noipa__)) u64 c0(u64 a,int n){return __ashldi3(a,n);}\n'
                'static __attribute__((__noinline__,__noipa__)) u64 c1(u64 a,int n){return __lshrdi3(a,n);}\n'
                'static __attribute__((__noinline__,__noipa__)) u64 c2(u64 a,int n){return __ashrdi3(a,n);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c3(s64 a,s64 b){return (unsigned)__cmpdi2(a,b);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c4(u64 a,u64 b){return (unsigned)__ucmpdi2(a,b);}\n'
                'static __attribute__((__noinline__,__noipa__)) u64 c5(u64 a){return __negdi2(a);}\n'),
        'calls': ('c0(cases[i].a,(int)cases[i].n)==cases[i].e0', 'c1(cases[i].a,(int)cases[i].n)==cases[i].e1',
                  'c2(cases[i].a,(int)cases[i].n)==cases[i].e2', 'c3((s64)cases[i].a,(s64)cases[i].b2)==cases[i].e3',
                  'c4(cases[i].a,cases[i].b2)==cases[i].e4', 'c5(cases[i].a)==cases[i].e5'),
    },
    'bitops': {
        'members': ('clz', 'clzsi2', 'clzdi2', 'ctzsi2', 'ctzdi2', 'clrsbsi2', 'clrsbdi2'),
        'decls': ('int __clzsi2(u32); int __clzdi2(u64); int __ctzsi2(u32); int __ctzdi2(u64);\n'
                  'int __clrsbsi2(u32); int __clrsbdi2(u64);\n'),
        'calcs': ('c0', 'c1', 'c2', 'c3', 'c4', 'c5'),
        'fns': ('static __attribute__((__noinline__,__noipa__)) unsigned c0(u32 a){return (unsigned)__clzsi2(a);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c1(u64 a){return (unsigned)__clzdi2(a);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c2(u32 a){return (unsigned)__ctzsi2(a);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c3(u64 a){return (unsigned)__ctzdi2(a);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c4(u32 a){return (unsigned)__clrsbsi2(a);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c5(u64 a){return (unsigned)__clrsbdi2(a);}\n'),
        'calls': ('c0((u32)cases[i].a)==cases[i].e0', 'c1(cases[i].a)==cases[i].e1',
                  'c2((u32)cases[i].a)==cases[i].e2', 'c3(cases[i].a)==cases[i].e3',
                  'c4((u32)cases[i].a)==cases[i].e4', 'c5(cases[i].a)==cases[i].e5'),
    },
    'ffs-a': {
        'members': ('clz', 'ffssi2', 'ffsdi2', 'popcountsi2', 'popcountdi2'),
        'decls': ('int __ffssi2(u32); int __ffsdi2(u64); int __popcountsi2(u32); int __popcountdi2(u64);\n'),
        'calcs': ('c0', 'c1', 'c2', 'c3'),
        'fns': ('static __attribute__((__noinline__,__noipa__)) unsigned c0(u32 a){return (unsigned)__ffssi2(a);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c1(u64 a){return (unsigned)__ffsdi2(a);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c2(u32 a){return (unsigned)__popcountsi2(a);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c3(u64 a){return (unsigned)__popcountdi2(a);}\n'),
        'calls': ('c0((u32)cases[i].a)==cases[i].e0', 'c1(cases[i].a)==cases[i].e1',
                  'c2((u32)cases[i].a)==cases[i].e2', 'c3(cases[i].a)==cases[i].e3'),
    },
    'ffs-b': {
        'members': ('paritysi2', 'paritydi2', 'bswapsi2', 'bswapdi2'),
        'decls': ('int __paritysi2(u32); int __paritydi2(u64); u32 __bswapsi2(u32); u64 __bswapdi2(u64);\n'),
        'calcs': ('c0', 'c1', 'c2', 'c3'),
        'fns': ('static __attribute__((__noinline__,__noipa__)) unsigned c0(u32 a){return (unsigned)__paritysi2(a);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c1(u64 a){return (unsigned)__paritydi2(a);}\n'
                'static __attribute__((__noinline__,__noipa__)) u32 c2(u32 a){return __bswapsi2(a);}\n'
                'static __attribute__((__noinline__,__noipa__)) u64 c3(u64 a){return __bswapdi2(a);}\n'),
        'calls': ('c0((u32)cases[i].a)==cases[i].e0', 'c1(cases[i].a)==cases[i].e1',
                  'c2((u32)cases[i].a)==(u32)cases[i].e2', 'c3(cases[i].a)==cases[i].e3'),
    },
    'divmod': {
        'members': ('clz', 'divmoddi4', 'udivmoddi4'),
        'checks': 4,
        'decls': ('s64 __divmoddi4(s64,s64,s64*); u64 __udivmoddi4(u64,u64,u64*);\n'),
        'calcs': ('c0', 'c1'),
        'fns': ('static __attribute__((__noinline__,__noipa__)) unsigned c0(u64 a,u64 b,u64 eq,u64 er)'
                '{u64 r;s64 q=__divmoddi4((s64)a,(s64)b,(s64*)&r);return (q==(s64)eq)+(r==er);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c1(u64 a,u64 b,u64 eq,u64 er)'
                '{u64 r;u64 q=__udivmoddi4(a,b,&r);return (q==eq)+(r==er);}\n'),
        'calls': ('c0(cases[i].a,cases[i].b,cases[i].e0,cases[i].e1)',
                  'c1(cases[i].a,cases[i].b,cases[i].e2,cases[i].e3)'),
    },
}


def reference_cases(group, seed):
    mask = (1 << 64) - 1
    if group in ('shifts', 'divmod'):
        rng = random.Random(seed)
        pairs = [(0, 1), (1, 1), (0xffffffffffffffff, 1), (0xffffffffffffffff, 0xffffffff),
                 (0x100000000, 0x10000), (0x8000000000000000, 3), (0x8000000000000000, 0xffffffff),
                 (0xffffffff, 0x100000000), (0x8000000000000000, 0x8000000000000000),
                 (0xffffffffffffffff, 0xffffffffffffffff)]
        pairs += [(rng.getrandbits(64), rng.getrandbits(64) or 1) for _ in range(50)]
        return pairs
    rng = random.Random(seed)
    if group == 'bitops':
        values = [0, 1, 2, 0x80000000, 0xffffffff, 0x8000000000000000, 0xffffffffffffffff,
                  0x100000000, 0x80000000, 0x7fffffff]
    else:
        values = [0, 1, 2, 3, 0x80000000, 0xffffffff, 0x8000000000000000, 0xffffffffffffffff,
                  0x100000000, 0x0102030405060708]
    values += [rng.getrandbits(64) for _ in range(50)]
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--units', type=Path, required=True,
                        help='directory produced by test_gcc_libgcc_units.py holding assembly.s per unit')
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--group', action='append', choices=sorted(GROUPS),
                        help='default: all groups whose members exist in --units')
    parser.add_argument('--seed', type=int, default=0x51f75)
    args = parser.parse_args()
    store = args.store.resolve()
    units = args.units.resolve()
    diagnostic = args.diagnostic.resolve()
    archive = store/NAME
    if not archive.is_file() or digest(archive, 'sha512') != SHA512:
        parser.error('changed pinned GCC archive')
    elf = diagnostic/'gcc-diagnostic.elf'
    prior = json.loads((diagnostic/'evidence.json').read_text())
    if not elf.is_file() or digest(elf) != prior['elf_sha256']:
        parser.error('changed diagnostic ELF')
    qemu = Path(json.loads((diagnostic/'command.json').read_text())[0])
    if not qemu.is_file() or digest(qemu) != prior['qemu_sha256']:
        parser.error('changed diagnostic qemu')
    wanted = args.group or [name for name in GROUPS
                             if all((units/u/'assembly.s').is_file() for u in GROUPS[name]['members'])]
    if not wanted:
        parser.error('no group fully present in --units')
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    import shutil
    shutil.copyfile(__file__, root/'run.py')
    summary = []
    for name in wanted:
        spec = GROUPS[name]
        folder = root/name
        folder.mkdir()
        members = []
        for unit in spec['members']:
            source = units/unit/'assembly.s'
            data = source.read_bytes()
            if not data:
                raise AssertionError('empty assembly: '+unit)
            (folder/(unit+'.s')).write_bytes(data)
            members.append(str(folder/(unit+'.s')))
        lib = folder/'libgcc.a'
        linked = subprocess.run(['ar', 'rcSD', str(lib)]+members, capture_output=True)
        if linked.returncode != 0:
            raise SystemExit(name+': ar failed: '+linked.stderr.decode(errors='replace')[:500])
        if name == 'shifts':
            mask = (1 << 64)-1
            pairs = reference_cases(name, args.seed)
            records = []
            for a, b in pairs:
                sa, sb = (a if a < 1 << 63 else a-(1 << 64)), (b if b < 1 << 63 else b-(1 << 64))
                quotient = (abs(sa)//abs(sb)) * (-1 if (sa < 0) != (sb < 0) else 1)
                n6 = b & 63
                records.append((a, n6, b, (a << n6) & mask, (a >> n6) & mask, (sa >> n6) & mask,
                                (1 if sa > sb else 0)-(1 if sa < sb else 0)+1,
                                (1 if a > b else 0)-(1 if a < b else 0)+1, (-a) & mask))
            header = ('typedef __UINT64_TYPE__ u64; typedef __INT64_TYPE__ s64;\n'
                      'u64 __ashldi3(u64,int); u64 __lshrdi3(u64,int); u64 __ashrdi3(u64,int);\n'
                      'int __cmpdi2(s64,s64); int __ucmpdi2(u64,u64); u64 __negdi2(u64);\n'
                      'struct record { u64 a; unsigned n; u64 b2; u64 e0,e1,e2; unsigned e3,e4; u64 e5; };\n')
            body = ['{%dULL,%d,%dULL,%dULL,%dULL,%dULL,%d,%d,%dULL}' % r for r in records]
        elif name == 'divmod':
            pairs = reference_cases(name, args.seed)
            mask = (1 << 64)-1
            records = []
            for a, b in pairs:
                sa, sb = (a if a < 1 << 63 else a-(1 << 64)), (b if b < 1 << 63 else b-(1 << 64))
                quotient = (abs(sa)//abs(sb)) * (-1 if (sa < 0) != (sb < 0) else 1)
                records.append((a, b, quotient & mask, (sa-quotient*sb) & mask, a//b, a % b))
            header = ('typedef __UINT64_TYPE__ u64; typedef __INT64_TYPE__ s64;\n' + spec['decls']
                      + 'struct record { u64 a,b,e0,e1,e2,e3; };\n')
            body = ['{%dULL,%dULL,%dULL,%dULL,%dULL,%dULL}' % r for r in records]
        else:
            values = reference_cases(name, args.seed)
            if name == 'bitops':
                records = [(a, clz32(a), clz64(a), ctz32(a), ctz64(a),
                            clrsb32(a), clrsb64(a)) for a in values]
            elif name == 'ffs-a':
                records = [(a, 0 if (a & 0xffffffff) == 0 else (a & 0xffffffff & -(a & 0xffffffff)).bit_length(),
                            0 if a == 0 else (a & -a).bit_length(),
                            bin(a & 0xffffffff).count('1'), bin(a).count('1')) for a in values]
            else:
                records = [(a, bin(a & 0xffffffff).count('1') & 1, bin(a).count('1') & 1,
                            bswap32(a), bswap64(a)) for a in values]
            nops = len(spec['calls'])
            header = ('typedef __UINT32_TYPE__ u32; typedef __UINT64_TYPE__ u64;\n' + spec['decls']
                      + 'struct record { u64 a; u64 ' + ','.join('e%d' % i for i in range(nops)) + '; };\n')
            body = ['{%dULL,%s}' % (r[0], ','.join('%dULL' % v for v in r[1:])) for r in records]
        text = header + 'static const struct record cases[]={' + ','.join(body) + '};\n' + spec['fns']
        text += 'unsigned value(void){unsigned p=0;for(unsigned i=0;i<%d;i++){' % len(records)
        for call in spec['calls']:
            text += 'p+=%s;' % call
        text += '}return p;}\n'
        data = text.encode()
        (folder/'main.c').write_bytes(data)
        incoming = pack(['cc1', '--space-program=result.s', '--space-entry=value', '--space-memory=65536',
                         '--space-library=libgcc.a', '-quiet', '-O2', '-ffreestanding', '-fno-builtin', '-nostdinc',
                         '-o', 'result.s', 'main.c'], {'main.c': data, 'libgcc.a': lib.read_bytes()})
        (folder/'job.bin').write_bytes(incoming)
        command = [str(qemu), '-strace', str(elf)]
        (folder/'command.json').write_text(json.dumps(command)+'\n')
        compiled = subprocess.run(command, input=incoming, capture_output=True, timeout=300)
        (folder/'response.bin').write_bytes(compiled.stdout)
        (folder/'syscalls.txt').write_bytes(compiled.stderr)
        if compiled.returncode != 0:
            raise SystemExit(name+': qemu exit %d' % compiled.returncode)
        code, stdout, stderr, image = decode(compiled.stdout)
        if not (code == 0 and not stdout and not stderr and image):
            raise SystemExit(name+': bad GCCOUT1 code=%d stderr=%r' % (code, stderr[:300]))
        (folder/'image.bin').write_bytes(image)
        emulator = ROOT/'build/bin/space-256m'
        direct = subprocess.run([str(emulator), '--ticks', '10000000', '--core', str(folder/'image.bin'),
                                 '--trace-channels', str(folder/'direct.trace')],
                                capture_output=True, timeout=300)
        (folder/'direct.out').write_bytes(direct.stdout)
        if direct.returncode != 0:
            raise SystemExit(name+': direct failed %d %r' % (direct.returncode, direct.stderr[:300]))
        expect = struct.pack('<I', len(records)*spec.get('checks', len(spec['calcs'])))
        if direct.stdout != expect or direct.stderr:
            raise SystemExit(name+': OUT mismatch %r vs %r err=%r'
                             % (direct.stdout, expect, direct.stderr[:200]))
        if (folder/'direct.trace').read_bytes()[-6:] != b' idle\n':
            raise SystemExit(name+': direct did not idle')
        record = {'group': name, 'cases': len(records), 'operations': spec.get('checks', len(spec['calcs'])),
                  'direct_result': len(records)*spec.get('checks', len(spec['calcs'])),
                  'archive_sha256': digest(lib), 'job_sha256': digest(folder/'job.bin'),
                  'image_sha256': digest(folder/'image.bin'), 'image_bytes': len(image)}
        (folder/'evidence.json').write_text(json.dumps(record, indent=2)+'\n')
        summary.append(record)
        print(name, 'direct checks', record['direct_result'], flush=True)
    (root/'evidence.json').write_text(json.dumps(
        {'scope': __doc__, 'gcc_archive_sha512': SHA512, 'groups': summary}, indent=2)+'\n')


if __name__ == '__main__':
    main()
