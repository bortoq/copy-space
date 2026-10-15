"""Link original fp-bit unsigned conversions and execute direct copies.

Takes usi_to_sf / usi_to_df sections compiled by test_gcc_libgcc_units.py
plus pack and clz helpers. Guards: validate inputs, check every
subprocess/file syscall, verify Python reference before asserting direct
OUT. QEMU diagnostic only. Expected SF bits are f32(float(iv));
DF bits are f64(float(iv)) for unsigned 32-bit inputs.
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

def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]

def b32(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]

def b64(x):
    return struct.unpack('<Q', struct.pack('<d', x))[0]

def run_one(qemu, elf, emu, lib_bytes, lib_name, main_c, sub, ncases):
    if not main_c or not lib_bytes:
        raise SystemExit("empty harness or library")
    sub.mkdir(parents=True, exist_ok=False)
    (sub/"main.c").write_bytes(main_c)
    incoming = pack(['cc1','--space-program=result.s','--space-entry=value','--space-memory=65536',
                     '--space-library='+lib_name,'-quiet','-O2','-ffreestanding','-fno-builtin','-nostdinc',
                     '-o','result.s','main.c'], {'main.c': main_c, lib_name: lib_bytes})
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
    parser.add_argument('--usi-sf-units', type=Path, required=True)
    parser.add_argument('--usi-df-units', type=Path, required=True)
    parser.add_argument('--sf-fine', type=Path, required=True)
    parser.add_argument('--df-fine', type=Path, required=True)
    parser.add_argument('--bit-units', type=Path, required=True)
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=0x451)
    args = parser.parse_args()
    usisf, usidf = args.usi_sf_units.resolve(), args.usi_df_units.resolve()
    sff, dff = args.sf_fine.resolve(), args.df_fine.resolve()
    bitd = args.bit_units.resolve()
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
    ivals = [0,1,2,127,255,65535,16777215,0x7fffffff,0x80000000,0xffffffff]
    ivals += [rng.getrandbits(32) for _ in range(50)]
    if len(ivals) != 60:
        raise SystemExit("bad case count")
    # SF
    members = []
    for src, name in [(usisf/"usi_to_sf"/"assembly.s","usi_to_sf.s"),
                      (sff/"pack_sf"/"assembly.s","pack_sf.s"),
                      (bitd/"clz"/"assembly.s","clz.s"),
                      (bitd/"clzsi2"/"assembly.s","clzsi2.s")]:
        if not src.is_file() or src.stat().st_size == 0:
            raise SystemExit(f"missing {name}")
        dst = probe/name
        dst.write_bytes(src.read_bytes())
        members.append(str(dst))
    lib = probe/"libgcc-usi-sf.a"
    r = subprocess.run(["ar","rcSD",str(lib)]+members, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"ar sf failed: {r.stderr[:500]}")
    libb = lib.read_bytes()
    text = ('typedef __UINT32_TYPE__ u32;\nu32 __floatunsisf(u32);\n'
            'struct record { u32 a,e; };\nstatic const struct record cases[]={')
    for iv in ivals:
        text += '{%dU,%dU},' % (iv & 0xffffffff, b32(f32(float(iv & 0xffffffff))))
    text += '};\nstatic __attribute__((__noinline__,__noipa__)) u32 c0(u32 a){return __floatunsisf(a);}\n'
    text += 'unsigned value(void){unsigned p=0;for(unsigned i=0;i<%d;i++){p+=c0(cases[i].a)==cases[i].e;}return p;}\n' % len(ivals)
    ev = run_one(qemu, elf, emu, libb, "libgcc-usi-sf.a", text.encode(), probe/"probe-sf", len(ivals))
    print(f"usi-sf: direct checks {ev['direct_result']}", flush=True)
    grand += ev['direct_result']
    # DF: reuse same ivals for determinism (rng already consumed, use fresh slice)
    members = []
    for src, name in [(usidf/"usi_to_df"/"assembly.s","usi_to_df.s"),
                      (dff/"pack_df"/"assembly.s","pack_df.s"),
                      (bitd/"clz"/"assembly.s","clz.s"),
                      (bitd/"clzsi2"/"assembly.s","clzsi2.s")]:
        # avoid overwrite of clz names: place in subdir via distinct probe? use same probe with df suffix
        dst = probe/("df-"+name)
        dst.write_bytes(src.read_bytes())
        members.append(str(dst))
    lib2 = probe/"libgcc-usi-df.a"
    r = subprocess.run(["ar","rcSD",str(lib2)]+members, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"ar df failed: {r.stderr[:500]}")
    libb2 = lib2.read_bytes()
    text = ('typedef __UINT32_TYPE__ u32; typedef __UINT64_TYPE__ u64;\nu64 __floatunsidf(unsigned);\n'
            'struct record { u32 a; u64 e; };\nstatic const struct record cases[]={')
    for iv in ivals:
        text += '{%dU,%dULL},' % (iv & 0xffffffff, b64(float(iv & 0xffffffff)))
    text += '};\nstatic __attribute__((__noinline__,__noipa__)) u64 c0(unsigned a){return __floatunsidf(a);}\n'
    text += 'unsigned value(void){unsigned p=0;for(unsigned i=0;i<%d;i++){p+=c0(cases[i].a)==cases[i].e;}return p;}\n' % len(ivals)
    ev = run_one(qemu, elf, emu, libb2, "libgcc-usi-df.a", text.encode(), probe/"probe-df", len(ivals))
    print(f"usi-df: direct checks {ev['direct_result']}", flush=True)
    grand += ev['direct_result']
    print(f"Original libgcc usi: direct checks {grand}")

if __name__ == "__main__":
    main()
