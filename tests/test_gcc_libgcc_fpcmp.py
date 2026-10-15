"""Link original fp-bit compare helpers and execute direct copies.

Takes comparison sections compiled by test_gcc_libgcc_units.py
(compare/ne/gt/ge/lt/le/unord for SF and DF) plus fine-grained helpers
(fpcmp_parts/unpack). Each sub-probe selects at most six library members
plus the explicit object, staying within the guest archive-linker cap of
twelve selected units. Guards: validate inputs, check every subprocess/file
syscall, verify Python reference before asserting direct OUT. QEMU is
diagnostic only. NaN inputs verify per-operation unordered branches:
compare/ne/lt/le yield 1, gt/ge yield -1 (0xffffffff), unord yields 1;
non-NaN results equal (a>b)-(a<b) as signed CMPtype.
"""
import argparse
import hashlib
import json
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

def is_nan_sf(b):
    return (b & 0x7f800000) == 0x7f800000 and (b & 0x007fffff) != 0

def is_nan_df(b):
    return (b & 0x7ff0000000000000) == 0x7ff0000000000000 and (b & 0x000fffffffffffff) != 0

def run_probe(qemu, elf, emu, lib_bytes, lib_name, main_c, probe_dir, nops, ncases):
    if not main_c or not lib_bytes:
        raise SystemExit("empty harness or library")
    if len(main_c) > 65536:
        raise SystemExit("harness too large")
    probe_dir.mkdir(parents=True, exist_ok=False)
    (probe_dir/"main.c").write_bytes(main_c)
    incoming = pack(['cc1','--space-program=result.s','--space-entry=value','--space-memory=65536',
                     '--space-library='+lib_name,'-quiet','-O2','-ffreestanding','-fno-builtin','-nostdinc',
                     '-o','result.s','main.c'], {'main.c': main_c, lib_name: lib_bytes})
    (probe_dir/"job.bin").write_bytes(incoming)
    cmd = [str(qemu),"-strace",str(elf)]
    (probe_dir/"command.json").write_text(json.dumps(cmd)+"\n")
    comp = subprocess.run(cmd, input=incoming, capture_output=True, timeout=300)
    (probe_dir/"response.bin").write_bytes(comp.stdout)
    (probe_dir/"syscalls.txt").write_bytes(comp.stderr)
    if comp.returncode != 0:
        raise SystemExit(f"qemu exit {comp.returncode}")
    code, stdout, stderr, image = decode(comp.stdout)
    if not (code == 0 and not stdout and not stderr and image):
        raise SystemExit(f"bad GCCOUT1 code={code} stderr={stderr[:400]!r}")
    (probe_dir/"image.bin").write_bytes(image)
    cmd2 = [str(emu),'--ticks','10000000','--core',str(probe_dir/"image.bin"),
            '--trace-channels',str(probe_dir/"direct.trace")]
    (probe_dir/"direct-command.json").write_text(json.dumps(cmd2)+"\n")
    d = subprocess.run(cmd2, capture_output=True, timeout=300)
    (probe_dir/"direct.out").write_bytes(d.stdout)
    if d.returncode != 0:
        raise SystemExit(f"direct failed {d.returncode} {d.stderr[:300]!r}")
    expect = struct.pack('<I', ncases*nops)
    if d.stdout != expect or d.stderr:
        raise SystemExit(f"OUT mismatch {d.stdout!r} vs {expect!r} err={d.stderr[:200]!r}")
    if (probe_dir/"direct.trace").read_bytes()[-6:] != b' idle\n':
        raise SystemExit("direct did not idle")
    ev = {'cases': ncases, 'operations': nops, 'direct_result': ncases*nops,
          'job_sha256': digest(probe_dir/"job.bin"),
          'image_sha256': digest(probe_dir/"image.bin"), 'image_bytes': len(image)}
    (probe_dir/"evidence.json").write_text(json.dumps(ev, indent=2)+"\n")
    return ev

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sf-units', type=Path, required=True,
                        help='SF comparison units dir (compare_sf, ne_sf, ...)')
    parser.add_argument('--df-units', type=Path, required=True)
    parser.add_argument('--sf-fine', type=Path, required=True,
                        help='SF fine units dir providing fpcmp_parts_sf and unpack_sf')
    parser.add_argument('--df-fine', type=Path, required=True)
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=0xf9c4)
    args = parser.parse_args()
    sfu, dfu = args.sf_units.resolve(), args.df_units.resolve()
    sff, dff = args.sf_fine.resolve(), args.df_fine.resolve()
    diag = args.diagnostic.resolve()
    elf = diag/"gcc-diagnostic.elf"
    prior = json.loads((diag/"evidence.json").read_text())
    if not elf.is_file() or digest(elf) != prior['elf_sha256']:
        parser.error('changed diagnostic ELF')
    qemu = Path(json.loads((diag/"command.json").read_text())[0])
    if not qemu.is_file() or digest(qemu) != prior['qemu_sha256']:
        parser.error('changed diagnostic qemu')
    emu = ROOT/"build/bin/space-256m"
    if not emu.is_file():
        raise SystemExit(f"missing emulator {emu}")
    probe = args.artifacts.resolve()
    probe.mkdir(parents=True, exist_ok=False)
    import shutil
    shutil.copyfile(__file__, probe/'run.py')
    grand = 0
    # SF archive: 7 comparisons + 2 helpers
    sf_members = []
    for unit in ("compare_sf","ne_sf","gt_sf","ge_sf","lt_sf","le_sf","unord_sf"):
        src = sfu/unit/"assembly.s"
        if not src.is_file() or src.stat().st_size == 0:
            raise SystemExit(f"missing SF section {unit}")
        dst = probe/(unit+".s")
        dst.write_bytes(src.read_bytes())
        sf_members.append(str(dst))
    for unit in ("fpcmp_parts_sf","unpack_sf"):
        src = sff/unit/"assembly.s"
        if not src.is_file() or src.stat().st_size == 0:
            raise SystemExit(f"missing SF helper {unit}")
        dst = probe/(unit+".s")
        dst.write_bytes(src.read_bytes())
        sf_members.append(str(dst))
    sf_lib = probe/"libgcc-fpcmp-sf.a"
    r = subprocess.run(["ar","rcSD",str(sf_lib)]+sf_members, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"ar sf failed: {r.stderr[:500]}")
    sf_lib_bytes = sf_lib.read_bytes()
    # DF archive
    df_members = []
    for unit in ("compare_df","ne_df","gt_df","ge_df","lt_df","le_df","unord_df"):
        src = dfu/unit/"assembly.s"
        if not src.is_file() or src.stat().st_size == 0:
            raise SystemExit(f"missing DF section {unit}")
        dst = probe/(unit+".s")
        dst.write_bytes(src.read_bytes())
        df_members.append(str(dst))
    for unit in ("fpcmp_parts_df","unpack_df"):
        src = dff/unit/"assembly.s"
        if not src.is_file() or src.stat().st_size == 0:
            raise SystemExit(f"missing DF helper {unit}")
        dst = probe/(unit+".s")
        dst.write_bytes(src.read_bytes())
        df_members.append(str(dst))
    df_lib = probe/"libgcc-fpcmp-df.a"
    r = subprocess.run(["ar","rcSD",str(df_lib)]+df_members, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"ar df failed: {r.stderr[:500]}")
    df_lib_bytes = df_lib.read_bytes()
    rng = random.Random(args.seed)
    # SF cases: 60 pairs including NaN/Inf/signed zeros
    NAN_SF = 0x7fc00000
    INF_SF = 0x7f800000
    NINF_SF = 0xff800000
    def f32bits(x):
        return struct.unpack('<I', struct.pack('<f', x))[0]
    fixed_sf = [(f32bits(1.5), f32bits(2.25)), (f32bits(0.0), f32bits(1.0)),
                (f32bits(-0.0), f32bits(0.0)), (INF_SF, NINF_SF), (NINF_SF, INF_SF),
                (INF_SF, INF_SF), (NAN_SF, f32bits(1.0)), (f32bits(1.0), NAN_SF),
                (NAN_SF, NAN_SF), (f32bits(-3.75), f32bits(0.5))]
    rand_sf = []
    for _ in range(50):
        a = struct.unpack('<I', struct.pack('<f', rng.uniform(-1000.0, 1000.0)))[0]
        b = struct.unpack('<I', struct.pack('<f', rng.uniform(-1000.0, 1000.0)))[0]
        rand_sf.append((a, b))
    sf_pairs = fixed_sf + rand_sf
    if len(sf_pairs) != 60:
        raise SystemExit("bad SF case count")
    # DF cases
    NAN_DF = 0x7ff8000000000000
    INF_DF = 0x7ff0000000000000
    NINF_DF = 0xfff0000000000000
    def f64bits(x):
        return struct.unpack('<Q', struct.pack('<d', x))[0]
    fixed_df = [(f64bits(1.5), f64bits(2.25)), (f64bits(0.0), f64bits(1.0)),
                (f64bits(-0.0), f64bits(0.0)), (INF_DF, NINF_DF), (NINF_DF, INF_DF),
                (INF_DF, INF_DF), (NAN_DF, f64bits(1.0)), (f64bits(1.0), NAN_DF),
                (NAN_DF, NAN_DF), (f64bits(-3.75), f64bits(0.5))]
    rand_df = []
    for _ in range(50):
        a = f64bits(rng.uniform(-1000.0, 1000.0))
        b = f64bits(rng.uniform(-1000.0, 1000.0))
        rand_df.append((a, b))
    df_pairs = fixed_df + rand_df
    if len(df_pairs) != 60:
        raise SystemExit("bad DF case count")
    def sf_expected(a, b):
        # returns (cmp, ne, gt, ge, lt, le, unord) as unsigned 32-bit
        if is_nan_sf(a) or is_nan_sf(b):
            return (1, 1, 0xffffffff, 0xffffffff, 1, 1, 1)
        fa = struct.unpack('<f', struct.pack('<I', a))[0]
        fb = struct.unpack('<f', struct.pack('<I', b))[0]
        c = (1 if fa > fb else 0) - (1 if fa < fb else 0)
        cu = c & 0xffffffff
        return (cu, cu, cu, cu, cu, cu, 0)
    def df_expected(a, b):
        if is_nan_df(a) or is_nan_df(b):
            return (1, 1, 0xffffffff, 0xffffffff, 1, 1, 1)
        fa = struct.unpack('<d', struct.pack('<Q', a))[0]
        fb = struct.unpack('<d', struct.pack('<Q', b))[0]
        c = (1 if fa > fb else 0) - (1 if fa < fb else 0)
        cu = c & 0xffffffff
        return (cu, cu, cu, cu, cu, cu, 0)
    # SF harness: split 4 + 3 to stay within 8 selected units
    sf_recs = [(a, b)+sf_expected(a, b) for a, b in sf_pairs]
    sf_header = ('typedef __UINT32_TYPE__ u32;\n'
                 'int __cmpsf2(u32,u32); int __nesf2(u32,u32); int __gtsf2(u32,u32); int __gesf2(u32,u32);\n'
                 'int __ltsf2(u32,u32); int __lesf2(u32,u32); int __unordsf2(u32,u32);\n'
                 'struct record { u32 a,b,e0,e1,e2,e3,e4,e5,e6; };\n'
                 'static const struct record cases[]={')
    for (a, b, e0, e1, e2, e3, e4, e5, e6) in sf_recs:
        sf_header += '{%dU,%dU,%dU,%dU,%dU,%dU,%dU,%dU,%dU},' % (a, b, e0, e1, e2, e3, e4, e5, e6)
    sf_header += '};\n'
    sf_calcs = ('static __attribute__((__noinline__,__noipa__)) unsigned c0(u32 a,u32 b){return (unsigned)__cmpsf2(a,b);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c1(u32 a,u32 b){return (unsigned)__nesf2(a,b);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c2(u32 a,u32 b){return (unsigned)__gtsf2(a,b);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c3(u32 a,u32 b){return (unsigned)__gesf2(a,b);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c4(u32 a,u32 b){return (unsigned)__ltsf2(a,b);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c5(u32 a,u32 b){return (unsigned)__lesf2(a,b);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c6(u32 a,u32 b){return (unsigned)__unordsf2(a,b);}\n')
    sf_loops = {
        'sf-a': ('p+=c0(cases[i].a,cases[i].b)==cases[i].e0;'
                 'p+=c1(cases[i].a,cases[i].b)==cases[i].e1;'
                 'p+=c2(cases[i].a,cases[i].b)==cases[i].e2;'
                 'p+=c3(cases[i].a,cases[i].b)==cases[i].e3;', 4),
        'sf-b': ('p+=c4(cases[i].a,cases[i].b)==cases[i].e4;'
                 'p+=c5(cases[i].a,cases[i].b)==cases[i].e5;'
                 'p+=c6(cases[i].a,cases[i].b)==cases[i].e6;', 3),
    }
    for suffix, (loop, nops) in sf_loops.items():
        text = sf_header + sf_calcs
        text += 'unsigned value(void){unsigned p=0;for(unsigned i=0;i<%d;i++){%s}return p;}\n' % (len(sf_recs), loop)
        ev = run_probe(qemu, elf, emu, sf_lib_bytes, "libgcc-fpcmp-sf.a", text.encode(), probe/("probe-"+suffix), nops, len(sf_recs))
        print(f"fpcmp-{suffix}: direct checks {ev['direct_result']}", flush=True)
        grand += ev['direct_result']
    df_recs = [(a, b)+df_expected(a, b) for a, b in df_pairs]
    df_header = ('typedef __UINT32_TYPE__ u32; typedef __UINT64_TYPE__ u64;\n'
                 'int __cmpdf2(u64,u64); int __nedf2(u64,u64); int __gtdf2(u64,u64); int __gedf2(u64,u64);\n'
                 'int __ltdf2(u64,u64); int __ledf2(u64,u64); int __unorddf2(u64,u64);\n'
                 'struct record { u64 a,b; u32 e0,e1,e2,e3,e4,e5,e6; };\n'
                 'static const struct record cases[]={')
    for (a, b, e0, e1, e2, e3, e4, e5, e6) in df_recs:
        df_header += '{%dULL,%dULL,%dU,%dU,%dU,%dU,%dU,%dU,%dU},' % (a, b, e0, e1, e2, e3, e4, e5, e6)
    df_header += '};\n'
    df_calcs = ('static __attribute__((__noinline__,__noipa__)) unsigned c0(u64 a,u64 b){return (unsigned)__cmpdf2(a,b);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c1(u64 a,u64 b){return (unsigned)__nedf2(a,b);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c2(u64 a,u64 b){return (unsigned)__gtdf2(a,b);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c3(u64 a,u64 b){return (unsigned)__gedf2(a,b);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c4(u64 a,u64 b){return (unsigned)__ltdf2(a,b);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c5(u64 a,u64 b){return (unsigned)__ledf2(a,b);}\n'
                'static __attribute__((__noinline__,__noipa__)) unsigned c6(u64 a,u64 b){return (unsigned)__unorddf2(a,b);}\n')
    df_loops = {
        'df-a': ('p+=c0(cases[i].a,cases[i].b)==cases[i].e0;'
                 'p+=c1(cases[i].a,cases[i].b)==cases[i].e1;'
                 'p+=c2(cases[i].a,cases[i].b)==cases[i].e2;'
                 'p+=c3(cases[i].a,cases[i].b)==cases[i].e3;', 4),
        'df-b': ('p+=c4(cases[i].a,cases[i].b)==cases[i].e4;'
                 'p+=c5(cases[i].a,cases[i].b)==cases[i].e5;'
                 'p+=c6(cases[i].a,cases[i].b)==cases[i].e6;', 3),
    }
    for suffix, (loop, nops) in df_loops.items():
        text = df_header + df_calcs
        text += 'unsigned value(void){unsigned p=0;for(unsigned i=0;i<%d;i++){%s}return p;}\n' % (len(df_recs), loop)
        ev = run_probe(qemu, elf, emu, df_lib_bytes, "libgcc-fpcmp-df.a", text.encode(), probe/("probe-"+suffix), nops, len(df_recs))
        print(f"fpcmp-{suffix}: direct checks {ev['direct_result']}", flush=True)
        grand += ev['direct_result']
    print(f"Original libgcc fpcmp: direct checks {grand}")

if __name__ == "__main__":
    main()
