"""Link original DI->float helpers and execute direct copies.

Takes floatdisf/floatdidf/floatundisf units compiled by
test_gcc_libgcc_units.py plus DF helpers (addsub/mul/si_to/
usi_to_df/pack/unpack/thenan/make, both float modes for the SF
targets) and integer helpers (muldi3/clzsi2/clz). Each probe selects
its closure with the guest linker; results execute as direct copies.
Guards: validate inputs, check every subprocess/file syscall, verify
Python reference before asserting direct OUT. QEMU diagnostic only.
Signed and unsigned 64-bit inputs are always defined for float
conversion (they round); the full ranges are covered.
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

def b32(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]

def b64(x):
    return struct.unpack('<Q', struct.pack('<d', x))[0]

def run_probe(qemu, elf, emu, lib_bytes, lib_name, main_c, sub, ncases):
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
    (sub/"evidence.json").write_text(json.dumps({'direct_result': ncases}, indent=2)+"\n")
    return ncases

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--floatdi-units', type=Path, required=True)
    parser.add_argument('--floatundi-units', type=Path, required=True)
    parser.add_argument('--df-fine', type=Path, required=True)
    parser.add_argument('--sf-fine', type=Path, required=True)
    parser.add_argument('--conv-sf-units', type=Path, required=True)
    parser.add_argument('--conv-df-units', type=Path, required=True)
    parser.add_argument('--usi-df-units', type=Path, required=True)
    parser.add_argument('--int-units', type=Path, required=True)
    parser.add_argument('--bit-units', type=Path, required=True)
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=0xd1f)
    args = parser.parse_args()
    fdi = args.floatdi_units.resolve()
    fundi = args.floatundi_units.resolve()
    dff = args.df_fine.resolve()
    sff = args.sf_fine.resolve()
    csf = args.conv_sf_units.resolve()
    cdf = args.conv_df_units.resolve()
    usi = args.usi_df_units.resolve()
    intd = args.int_units.resolve()
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
    helpers = [(dff/"addsub_df"/"assembly.s","addsub_df.s"),
               (dff/"mul_df"/"assembly.s","mul_df.s"),
               (dff/"si_to_df"/"assembly.s","si_to_df.s"),
               (usi/"usi_to_df"/"assembly.s","usi_to_df.s"),
               (cdf/"df_to_sf"/"assembly.s","df_to_sf.s"),
               (dff/"pack_df"/"assembly.s","pack_df.s"),
               (dff/"unpack_df"/"assembly.s","unpack_df.s"),
               (dff/"thenan_df"/"assembly.s","thenan_df.s"),
               (dff/"make_df"/"assembly.s","make_df.s"),
               (sff/"pack_sf"/"assembly.s","pack_sf.s"),
               (sff/"unpack_sf"/"assembly.s","unpack_sf.s"),
               (sff/"thenan_sf"/"assembly.s","thenan_sf.s"),
               (sff/"make_sf"/"assembly.s","make_sf.s"),
               (intd/"muldi3"/"assembly.s","muldi3.s"),
               (bitd/"clzsi2"/"assembly.s","clzsi2.s"),
               (bitd/"clz"/"assembly.s","clz.s")]
    for src, name in helpers:
        if not src.is_file() or src.stat().st_size == 0:
            raise SystemExit(f"missing helper {name}")
    rng = random.Random(args.seed)
    grand = 0
    # probe 1: floatdisf (s64 -> float bits)
    sub = probe/"probe-disf"
    sub.mkdir()
    members = []
    for src, name in [(fdi/"floatdisf"/"assembly.s","floatdisf.s")] + helpers:
        dst = sub/name
        dst.write_bytes(src.read_bytes())
        members.append(str(dst))
    lib = sub/"libgcc-floatdi.a"
    r = subprocess.run(["ar","rcSD",str(lib)]+members, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"ar disf failed: {r.stderr[:500]}")
    svals = [0,1,-1,127,-128,2147483647,-2147483648,9223372036854775807,(-9223372036854775807 - 1),4294967296]
    svals += [rng.getrandbits(64) - (1 << 63) if rng.getrandbits(1) else rng.getrandbits(63) for _ in range(50)]
    svals = [v - (1 << 64) if v >= (1 << 63) else v for v in svals]
    assert len(svals) == 60
    text = ('typedef __UINT32_TYPE__ u32; typedef __INT64_TYPE__ s64;\n'
            'typedef __INT64_TYPE__ s64m;\n'
            'u32 __floatdisf(s64);\n'
            'struct record { s64 a; u32 e; };\nstatic const struct record cases[]={')
    def s64lit(v):
        return '(-9223372036854775807LL-1)' if v == -(1 << 63) else '%dLL' % v
    for v in svals:
        text += '{%s,%dU},' % (s64lit(v), b32(float(v)))
    text += '};\nstatic __attribute__((__noinline__,__noipa__)) u32 c0(s64 a){return __floatdisf(a);}\n'
    text += 'unsigned value(void){unsigned p=0;for(unsigned i=0;i<%d;i++){p+=c0(cases[i].a)==cases[i].e;}return p;}\n' % len(svals)
    grand += run_probe(qemu, elf, emu, lib.read_bytes(), "libgcc-floatdi.a", text.encode(), sub/"run", len(svals))
    print(f"floatdisf: direct checks {len(svals)}", flush=True)
    # probe 2: floatdidf (s64 -> double bits)
    sub = probe/"probe-didf"
    sub.mkdir()
    members = []
    for src, name in [(fdi/"floatdidf"/"assembly.s","floatdidf.s")] + helpers:
        dst = sub/name
        dst.write_bytes(src.read_bytes())
        members.append(str(dst))
    lib = sub/"libgcc-floatdi2.a"
    r = subprocess.run(["ar","rcSD",str(lib)]+members, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"ar didf failed: {r.stderr[:500]}")
    text = ('typedef __UINT64_TYPE__ u64; typedef __INT64_TYPE__ s64;\nu64 __floatdidf(s64);\n'
            'struct record { s64 a; u64 e; };\nstatic const struct record cases[]={')
    for v in svals:
        text += '{%s,%dULL},' % (s64lit(v), b64(float(v)))
    text += '};\nstatic __attribute__((__noinline__,__noipa__)) u64 c0(s64 a){return __floatdidf(a);}\n'
    text += 'unsigned value(void){unsigned p=0;for(unsigned i=0;i<%d;i++){p+=c0(cases[i].a)==cases[i].e;}return p;}\n' % len(svals)
    grand += run_probe(qemu, elf, emu, lib.read_bytes(), "libgcc-floatdi2.a", text.encode(), sub/"run", len(svals))
    print(f"floatdidf: direct checks {len(svals)}", flush=True)
    # probe 3: floatundisf (u64 -> float bits)
    sub = probe/"probe-undisf"
    sub.mkdir()
    members = []
    for src, name in [(fundi/"floatundisf"/"assembly.s","floatundisf.s")] + helpers:
        dst = sub/name
        dst.write_bytes(src.read_bytes())
        members.append(str(dst))
    lib = sub/"libgcc-floatundi3.a"
    r = subprocess.run(["ar","rcSD",str(lib)]+members, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"ar undisf failed: {r.stderr[:500]}")
    uvals = [0,1,2,127,255,65535,4294967295,4294967296,18446744073709551615,9223372036854775808]
    uvals += [rng.getrandbits(64) for _ in range(50)]
    assert len(uvals) == 60
    text = ('typedef __UINT32_TYPE__ u32; typedef __UINT64_TYPE__ u64;\nu32 __floatundisf(u64);\n'
            'struct record { u64 a; u32 e; };\nstatic const struct record cases[]={')
    for v in uvals:
        text += '{%dULL,%dU},' % (v, b32(float(v)))
    text += '};\nstatic __attribute__((__noinline__,__noipa__)) u32 c0(u64 a){return __floatundisf(a);}\n'
    text += 'unsigned value(void){unsigned p=0;for(unsigned i=0;i<%d;i++){p+=c0(cases[i].a)==cases[i].e;}return p;}\n' % len(uvals)
    grand += run_probe(qemu, elf, emu, lib.read_bytes(), "libgcc-floatundi3.a", text.encode(), sub/"run", len(uvals))
    print(f"floatundisf: direct checks {len(uvals)}", flush=True)
    print(f"Original libgcc floatdi: direct checks {grand}")

if __name__ == "__main__":
    main()
