"""Link fp-bit SF<->DF conversions and execute direct copies.

Guards: validate inputs, check every subprocess/file syscall, verify
Python reference before asserting direct OUT. QEMU diagnostic only.
Overflow double->float yields inf; NaN inputs are excluded.
"""
import argparse
import hashlib
import json
import math
import random
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/user/work/copy-space")
sys.path.insert(0, str(ROOT/"tests"))
from test_gcc_linux_units import pack
from test_gcc_copy_output import decode

def digest(path, algo="sha256"):
    if not path.is_file():
        raise SystemExit(f"missing file: {path}")
    with path.open("rb") as s:
        return hashlib.file_digest(s, algo).hexdigest()

def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]

def b32(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def f32t(d):
    try:
        return struct.unpack('<f', struct.pack('<f', d))[0]
    except OverflowError:
        return math.copysign(math.inf, d)

def b64(x):
    return struct.unpack('<Q', struct.pack('<d', x))[0]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--conv-sf-units', type=Path, required=True,
                        help='sf_to_df unit dir from test_gcc_libgcc_units.py')
    parser.add_argument('--conv-df-units', type=Path, required=True,
                        help='df_to_sf unit dir from test_gcc_libgcc_units.py')
    parser.add_argument('--sf-units', type=Path, required=True,
                        help='fine-grained sf units dir (pack/unpack/make/thenan)')
    parser.add_argument('--df-units', type=Path, required=True,
                        help='fine-grained df units dir (pack/unpack/make/thenan)')
    parser.add_argument('--int-units', type=Path, required=True,
                        help='integer units dir providing muldi3')
    parser.add_argument('--bit-units', type=Path, required=True,
                        help='bitops units dir providing clz and clzsi2')
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=0xc0e)
    args = parser.parse_args()
    sfsrc, dfsrc = args.conv_sf_units.resolve(), args.conv_df_units.resolve()
    sfdir, dfdir = args.sf_units.resolve(), args.df_units.resolve()
    intdir, bitdir = args.int_units.resolve(), args.bit_units.resolve()
    diag = args.diagnostic.resolve()
    elf = diag/"gcc-diagnostic.elf"
    prior = json.loads((diag/"evidence.json").read_text())
    if not elf.is_file() or digest(elf) != prior['elf_sha256']:
        parser.error('changed diagnostic ELF')
    qemu = Path(json.loads((diag/"command.json").read_text())[0])
    if not qemu.is_file() or digest(qemu) != prior['qemu_sha256']:
        parser.error('changed diagnostic qemu')
    probe = args.artifacts.resolve()
    probe.mkdir(parents=True, exist_ok=False)
    import shutil
    shutil.copyfile(__file__, probe/'run.py')
    members = []
    wanted = [(sfsrc/"sf_to_df"/"assembly.s", "sf_to_df.s"),
              (dfsrc/"df_to_sf"/"assembly.s", "df_to_sf.s"),
              (sfdir/"unpack_sf"/"assembly.s", "unpack_sf.s"),
              (sfdir/"pack_sf"/"assembly.s", "pack_sf.s"),
              (sfdir/"make_sf"/"assembly.s", "make_sf.s"),
              (sfdir/"thenan_sf"/"assembly.s", "thenan_sf.s"),
              (dfdir/"unpack_df"/"assembly.s", "unpack_df.s"),
              (dfdir/"pack_df"/"assembly.s", "pack_df.s"),
              (dfdir/"make_df"/"assembly.s", "make_df.s"),
              (dfdir/"thenan_df"/"assembly.s", "thenan_df.s"),
              (intdir/"muldi3"/"assembly.s", "muldi3.s"),
              (bitdir/"clz"/"assembly.s", "clz.s"),
              (bitdir/"clzsi2"/"assembly.s", "clzsi2.s")]
    for src, name in wanted:
        if not src.is_file() or src.stat().st_size == 0:
            raise SystemExit(f"missing member {name}")
        dst = probe/name
        dst.write_bytes(src.read_bytes())
        members.append(str(dst))
    lib = probe/"libgcc-conv.a"
    r = subprocess.run(["ar","rcSD",str(lib)]+members, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"ar failed: {r.stderr[:500]}")
    rng = random.Random(args.seed)
    fvals = [0.0, -0.0, 1.0, -1.0, 0.5, 1.5, 100.125, 65536.0, 1e10, 1e-10,
             3.14159265, -2.71828, 16777216.0, 0.1]
    fvals += [rng.uniform(-1000.0, 1000.0) for _ in range(46)]
    dvals = [0.0, 1.0, -1.0, 0.1, 1/3, 1e100, -1e100, 1e300, -1e300, 1e-300,
             123.456789012345, -987.654321, 16777217.0, 0.5]
    dvals += [rng.uniform(-1000.0, 1000.0) for _ in range(46)]
    if len(fvals) != 60 or len(dvals) != 60:
        raise SystemExit("bad case count")
    recs = [(b32(f32(f)), b64(d), b64(float(f32(f))), b32(f32t(d))) for f, d in zip(fvals, dvals)]
    text = ('typedef __UINT32_TYPE__ u32; typedef __UINT64_TYPE__ u64;\n'
            'u64 __extendsfdf2(u32); u32 __truncdfsf2(u64);\n'
            'struct record { u32 f; u64 d; u64 ee; u32 et; };\n'
            'static const struct record cases[]={')
    for (f, d, ee, et) in recs:
        text += '{%dU,%dULL,%dULL,%dU},' % (f, d, ee, et)
    text += '};\n'
    text += ('static __attribute__((__noinline__,__noipa__)) u64 c0(u32 a){return __extendsfdf2(a);}\n'
             'static __attribute__((__noinline__,__noipa__)) u32 c1(u64 a){return __truncdfsf2(a);}\n'
             'unsigned value(void){unsigned p=0;for(unsigned i=0;i<%d;i++){' % len(recs))
    loops = {'ext': 'p+=c0(cases[i].f)==cases[i].ee;}return p;}\n',
               'trunc': 'p+=c1(cases[i].d)==cases[i].et;}return p;}\n'}
    grand = 0
    for suffix, tail in loops.items():
        sub = probe/("probe-"+suffix)
        sub.mkdir()
        data = (text + tail).encode()
        (sub/"main.c").write_bytes(data)
        incoming = pack(['cc1','--space-program=result.s','--space-entry=value','--space-memory=65536',
                         '--space-library=libgcc-conv.a','-quiet','-O2','-ffreestanding','-fno-builtin','-nostdinc',
                         '-o','result.s','main.c'], {'main.c': data, 'libgcc-conv.a': lib.read_bytes()})
        (sub/"job.bin").write_bytes(incoming)
        cmd = [str(qemu),"-strace",str(elf)]
        (sub/"command.json").write_text(json.dumps(cmd)+"\n")
        comp = subprocess.run(cmd, input=incoming, capture_output=True, timeout=300)
        (sub/"response.bin").write_bytes(comp.stdout)
        (sub/"syscalls.txt").write_bytes(comp.stderr)
        if comp.returncode != 0:
            raise SystemExit(f"{suffix}: qemu exit {comp.returncode}")
        code, stdout, stderr, image = decode(comp.stdout)
        if not (code == 0 and not stdout and not stderr and image):
            raise SystemExit(f"{suffix}: bad GCCOUT1 code={code} stderr={stderr[:400]!r}")
        (sub/"image.bin").write_bytes(image)
        emu = ROOT/"build/bin/space-256m"
        cmd2 = [str(emu),'--ticks','10000000','--core',str(sub/"image.bin"),
                '--trace-channels',str(sub/"direct.trace")]
        (sub/"direct-command.json").write_text(json.dumps(cmd2)+"\n")
        d = subprocess.run(cmd2, capture_output=True, timeout=300)
        (sub/"direct.out").write_bytes(d.stdout)
        if d.returncode != 0:
            raise SystemExit(f"{suffix}: direct failed {d.returncode} {d.stderr[:300]!r}")
        expect = struct.pack('<I', len(recs))
        if d.stdout != expect or d.stderr:
            raise SystemExit(f"{suffix}: OUT mismatch {d.stdout!r} vs {expect!r} err={d.stderr[:200]!r}")
        if (sub/"direct.trace").read_bytes()[-6:] != b' idle\n':
            raise SystemExit(f"{suffix}: direct did not idle")
        ev = {'sub': suffix, 'cases': len(recs), 'operations': 1, 'direct_result': len(recs),
              'archive_sha256': digest(lib), 'job_sha256': digest(sub/"job.bin"),
              'image_sha256': digest(sub/"image.bin"), 'image_bytes': len(image)}
        (sub/"evidence.json").write_text(json.dumps(ev, indent=2)+"\n")
        print(f"conv-{suffix}: direct checks {len(recs)}", flush=True)
        grand += len(recs)
    print(f"Original libgcc fp-conv: direct checks {grand}")

if __name__ == "__main__":
    main()
