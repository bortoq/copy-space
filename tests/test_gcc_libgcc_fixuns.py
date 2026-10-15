"""Link original fixuns float->unsigned helpers and execute direct copies.

Takes fixunssfsi/fixunsdfsi units compiled by test_gcc_libgcc_units.py
plus fine-grained fp helpers (ge/addsub/to_si/fpcmp_parts/unpack/pack/
thenan). Each probe selects eight library members plus the explicit
object (nine total), within the twelve-unit guest archive-linker cap.
Guards: validate inputs, check every subprocess/file syscall, verify
Python reference before asserting direct OUT. QEMU diagnostic only.
Inputs stay in [0, 2**32): negatives, NaN, Inf and out-of-range floats
are excluded (C conversion there is undefined).
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

def run_one(qemu, elf, emu, lib_bytes, lib_name, main_c, sub, ncases, *, installed=False):
    if not main_c or not lib_bytes:
        raise SystemExit("empty harness or library")
    sub.mkdir(parents=True, exist_ok=False)
    (sub/"main.c").write_bytes(main_c)
    options = [] if installed else ['--space-library='+lib_name]
    files = {'main.c': main_c}
    if not installed:
        files[lib_name] = lib_bytes
    incoming = pack(['cc1','--space-program=result.s','--space-entry=value','--space-memory=65536']+
                    options+['-quiet','-O2','-ffreestanding','-fno-builtin','-nostdinc',
                     '-o','result.s','main.c'], files)
    (sub/"job.bin").write_bytes(incoming)
    cmd = [str(qemu),"-strace",str(elf)]
    (sub/"command.json").write_text(json.dumps(cmd)+"\n")
    comp = subprocess.run(cmd, input=incoming, capture_output=True, timeout=300)
    (sub/"response.bin").write_bytes(comp.stdout)
    (sub/"syscalls.txt").write_bytes(comp.stderr)
    if comp.returncode != 0:
        raise SystemExit(f"qemu exit {comp.returncode}")
    code, stdout, stderr, image = decode(comp.stdout)
    if not (code == 0 and not stdout and not stderr and image):
        raise SystemExit(f"bad GCCOUT1 code={code} stderr={stderr[:400]!r}")
    (sub/"image.bin").write_bytes(image)
    cmd2 = [str(emu),'--ticks','10000000','--core',str(sub/"image.bin"),
            '--trace-channels',str(sub/"direct.trace")]
    (sub/"direct-command.json").write_text(json.dumps(cmd2)+"\n")
    d = subprocess.run(cmd2, capture_output=True, timeout=300)
    (sub/"direct.out").write_bytes(d.stdout)
    if d.returncode != 0:
        raise SystemExit(f"direct failed {d.returncode} {d.stderr[:300]!r}")
    expect = struct.pack('<I', ncases)
    if d.stdout != expect or d.stderr:
        raise SystemExit(f"OUT mismatch {d.stdout!r} vs {expect!r} err={d.stderr[:200]!r}")
    if (sub/"direct.trace").read_bytes()[-6:] != b' idle\n':
        raise SystemExit("direct did not idle")
    ev = {'cases': ncases, 'operations': 1, 'direct_result': ncases,
          'job_sha256': digest(sub/"job.bin"),
          'image_sha256': digest(sub/"image.bin"), 'image_bytes': len(image)}
    (sub/"evidence.json").write_text(json.dumps(ev, indent=2)+"\n")
    return ev

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixuns-units', type=Path, required=True,
                        help='units dir with fixunssfsi/fixunsdfsi assembly.s')
    parser.add_argument('--sf-fine', type=Path, required=True)
    parser.add_argument('--df-fine', type=Path, required=True)
    parser.add_argument('--sf-cmp', type=Path, required=True,
                        help='SF comparison units dir providing ge_sf')
    parser.add_argument('--df-cmp', type=Path, required=True)
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=0xf17)
    args = parser.parse_args()
    fixd = args.fixuns_units.resolve()
    sff, dff = args.sf_fine.resolve(), args.df_fine.resolve()
    sfc, dfc = args.sf_cmp.resolve(), args.df_cmp.resolve()
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
    rng = random.Random(args.seed)
    # SF cases: floats in [0, 2**32)
    def f32(x):
        return struct.unpack('<f', struct.pack('<f', x))[0]
    fixed_sf = [0.0, 1.0, 2.0, 127.0, 255.0, 65535.0, 16777215.0, 16777216.0,
                2147483648.0, 4000000000.0]
    sf_vals = list(fixed_sf)
    while len(sf_vals) < 60:
        v = f32(rng.uniform(0, 4000000000.0))
        if v < 0 or v >= 4294967296.0:
            continue
        sf_vals.append(v)
    sf_recs = [(struct.unpack('<I', struct.pack('<f', v))[0], int(v) & 0xffffffff) for v in sf_vals]
    if len(sf_recs) != 60:
        raise SystemExit("bad SF case count")
    members = []
    for src, name in [(fixd/"fixunssfsi"/"assembly.s","fixunssfsi.s"),
                      (sfc/"ge_sf"/"assembly.s","ge_sf.s"),
                      (sff/"addsub_sf"/"assembly.s","addsub_sf.s"),
                      (sff/"sf_to_si"/"assembly.s","sf_to_si.s"),
                      (sff/"fpcmp_parts_sf"/"assembly.s","fpcmp_parts_sf.s"),
                      (sff/"unpack_sf"/"assembly.s","unpack_sf.s"),
                      (sff/"pack_sf"/"assembly.s","pack_sf.s"),
                      (sff/"thenan_sf"/"assembly.s","thenan_sf.s")]:
        if not src.is_file() or src.stat().st_size == 0:
            raise SystemExit(f"missing SF member {name}")
        dst = probe/name
        dst.write_bytes(src.read_bytes())
        members.append(str(dst))
    lib = probe/"libgcc-fixuns-sf.a"
    r = subprocess.run(["ar","rcSD",str(lib)]+members, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"ar sf failed: {r.stderr[:500]}")
    libb = lib.read_bytes()
    text = ('typedef __UINT32_TYPE__ u32;\nu32 __fixunssfsi(u32);\n'
            'struct record { u32 a,e; };\nstatic const struct record cases[]={')
    for a, e in sf_recs:
        text += '{%dU,%dU},' % (a, e)
    text += '};\nstatic __attribute__((__noinline__,__noipa__)) u32 c0(u32 a){return __fixunssfsi(a);}\n'
    text += 'unsigned value(void){unsigned p=0;for(unsigned i=0;i<%d;i++){p+=c0(cases[i].a)==cases[i].e;}return p;}\n' % len(sf_recs)
    ev = run_one(qemu, elf, emu, libb, "libgcc-fixuns-sf.a", text.encode(), probe/"probe-sf", len(sf_recs))
    print(f"fixuns-sf: direct checks {ev['direct_result']}", flush=True)
    grand += ev['direct_result']
    # DF cases
    fixed_df = [0.0, 1.0, 2.0, 127.0, 255.0, 65535.0, 16777215.0, 16777216.0,
                2147483648.0, 4294967295.0]
    df_vals = list(fixed_df)
    while len(df_vals) < 60:
        v = rng.uniform(0, 4294967295.0)
        if v < 0 or v >= 4294967296.0:
            continue
        df_vals.append(v)
    df_recs = [(struct.unpack('<Q', struct.pack('<d', v))[0], int(v) & 0xffffffff) for v in df_vals]
    if len(df_recs) != 60:
        raise SystemExit("bad DF case count")
    members = []
    for src, name in [(fixd/"fixunsdfsi"/"assembly.s","fixunsdfsi.s"),
                      (dfc/"ge_df"/"assembly.s","ge_df.s"),
                      (dff/"addsub_df"/"assembly.s","addsub_df.s"),
                      (dff/"df_to_si"/"assembly.s","df_to_si.s"),
                      (dff/"fpcmp_parts_df"/"assembly.s","fpcmp_parts_df.s"),
                      (dff/"unpack_df"/"assembly.s","unpack_df.s"),
                      (dff/"pack_df"/"assembly.s","pack_df.s"),
                      (dff/"thenan_df"/"assembly.s","thenan_df.s")]:
        if not src.is_file() or src.stat().st_size == 0:
            raise SystemExit(f"missing DF member {name}")
        dst = probe/("df-"+name)
        dst.write_bytes(src.read_bytes())
        members.append(str(dst))
    lib2 = probe/"libgcc-fixuns-df.a"
    r = subprocess.run(["ar","rcSD",str(lib2)]+members, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"ar df failed: {r.stderr[:500]}")
    libb2 = lib2.read_bytes()
    text = ('typedef __UINT32_TYPE__ u32; typedef __UINT64_TYPE__ u64;\nu32 __fixunsdfsi(u64);\n'
            'struct record { u64 a; u32 e; };\nstatic const struct record cases[]={')
    for a, e in df_recs:
        text += '{%dULL,%dU},' % (a, e)
    text += '};\nstatic __attribute__((__noinline__,__noipa__)) u32 c0(u64 a){return __fixunsdfsi(a);}\n'
    text += 'unsigned value(void){unsigned p=0;for(unsigned i=0;i<%d;i++){p+=c0(cases[i].a)==cases[i].e;}return p;}\n' % len(df_recs)
    ev = run_one(qemu, elf, emu, libb2, "libgcc-fixuns-df.a", text.encode(), probe/"probe-df", len(df_recs))
    print(f"fixuns-df: direct checks {ev['direct_result']}", flush=True)
    grand += ev['direct_result']
    print(f"Original libgcc fixuns: direct checks {grand}")

if __name__ == "__main__":
    main()
