"""Link original fp-bit single-float helpers and execute direct copies.

The guest archive linker caps selected units at twelve including the
explicit object, so arithmetic (add/sub/mul/div) and compare/convert
(eq/fix/floatsisf) ride in two sub-probes sharing one archive of
fine-grained fp-bit sections plus integer helpers.
Guards: validate inputs, check every subprocess/file syscall, verify
Python reference before asserting direct OUT. QEMU diagnostic only.
Compares avoid NaN (eq returns nonzero there by design); division keeps
results in the normal range; fix inputs stay within int range.
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

def bits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--units', type=Path, required=True,
                        help='fine-grained fp-bit units dir from test_gcc_libgcc_units.py (addsub_sf, mul_sf, ...)')
    parser.add_argument('--int-units', type=Path, required=True,
                        help='integer units dir providing muldi3')
    parser.add_argument('--bit-units', type=Path, required=True,
                        help='bitops units dir providing clz and clzsi2')
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=0xf10a7)
    args = parser.parse_args()
    fine, intdir, bitdir = args.units.resolve(), args.int_units.resolve(), args.bit_units.resolve()
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
    sections = ("addsub_sf", "mul_sf", "div_sf", "eq_sf", "fpcmp_parts_sf", "pack_sf", "unpack_sf",
                "thenan_sf", "make_sf", "negate_sf", "sf_to_si", "si_to_sf")
    for unit in sections:
        src = fine/unit/"assembly.s"
        if not src.is_file() or src.stat().st_size == 0:
            raise SystemExit(f"missing section {unit}")
        dst = probe/(unit+".s")
        dst.write_bytes(src.read_bytes())
        members.append(str(dst))
    for src, name in [(intdir/"muldi3"/"assembly.s", "muldi3.s"),
                      (bitdir/"clz"/"assembly.s", "clz.s"),
                      (bitdir/"clzsi2"/"assembly.s", "clzsi2.s")]:
        if not src.is_file() or src.stat().st_size == 0:
            raise SystemExit(f"missing helper {name}")
        dst = probe/name
        dst.write_bytes(src.read_bytes())
        members.append(str(dst))
    lib = probe/"libgcc-float.a"
    r = subprocess.run(["ar","rcSD",str(lib)]+members, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"ar failed: {r.stderr[:500]}")
    rng = random.Random(args.seed)
    pairs = [(1.5, 2.25), (0.0, 1.0), (-3.75, 0.5), (100.125, -0.25), (1.0, 3.0),
             (65536.0, 2.0), (0.1, 0.2), (-0.0, 5.0), (123456.0, 7.0), (2.5, -2.5)]
    pairs += [(rng.uniform(-1000.0, 1000.0), rng.uniform(0.5, 1000.0)*(1 if rng.getrandbits(1) else -1))
              for _ in range(50)]
    if len(pairs) != 60:
        raise SystemExit("bad case count")
    ivals = [0, 1, -1, 127, -128, 12345, -12345, 16777215, -16777215, 42]
    ivals += [rng.randint(-16777215, 16777215) for _ in range(50)]
    recs = []
    for (a, b), iv in zip(pairs, ivals):
        fa, fb = f32(a), f32(b)
        eq = 0 if fa == fb else (1 if fa > fb else 0xffffffff)
        recs.append((struct.unpack('<I', struct.pack('<f', fa))[0],
                     struct.unpack('<I', struct.pack('<f', fb))[0],
                     bits(fa+fb), bits(fa-fb), bits(fa*fb), bits(fa/fb),
                     eq, int(fa) & 0xffffffff, bits(float(iv)), iv & 0xffffffff))
    header = ('typedef __UINT32_TYPE__ u32;\n'
              'u32 __addsf3(u32,u32); u32 __subsf3(u32,u32); u32 __mulsf3(u32,u32); u32 __divsf3(u32,u32);\n'
              'int __eqsf2(u32,u32); int __fixsfsi(u32); u32 __floatsisf(int);\n'
              'struct record { u32 a,b,e0,e1,e2,e3,e4,e5,e6,iv; };\n'
              'static const struct record cases[]={')
    for (a,b,ea,es,em,ed,eq,fx,e6,iv) in recs:
        header += '{%dU,%dU,%dU,%dU,%dU,%dU,%dU,%dU,%dU,%dU},' % (a,b,ea,es,em,ed,eq,fx,e6,iv)
    header += '};\n'
    calcs = ('static __attribute__((__noinline__,__noipa__)) u32 c0(u32 a,u32 b){return __addsf3(a,b);}\n'
             'static __attribute__((__noinline__,__noipa__)) u32 c1(u32 a,u32 b){return __subsf3(a,b);}\n'
             'static __attribute__((__noinline__,__noipa__)) u32 c2(u32 a,u32 b){return __mulsf3(a,b);}\n'
             'static __attribute__((__noinline__,__noipa__)) u32 c3(u32 a,u32 b){return __divsf3(a,b);}\n'
             'static __attribute__((__noinline__,__noipa__)) unsigned c4(u32 a,u32 b){return (unsigned)__eqsf2(a,b);}\n'
             'static __attribute__((__noinline__,__noipa__)) int c5(u32 a){return __fixsfsi(a);}\n'
             'static __attribute__((__noinline__,__noipa__)) u32 c6(int a){return __floatsisf(a);}\n')
    loops = {
        'a': ('p+=c0(cases[i].a,cases[i].b)==cases[i].e0;'
              'p+=c1(cases[i].a,cases[i].b)==cases[i].e1;'
              'p+=c2(cases[i].a,cases[i].b)==cases[i].e2;'
              'p+=c3(cases[i].a,cases[i].b)==cases[i].e3;', 4),
        'b1': ('p+=c4(cases[i].a,cases[i].b)==cases[i].e4;', 1),
        'b2': ('p+=c5(cases[i].a)==(int)cases[i].e5;'
               'p+=c6((int)cases[i].iv)==cases[i].e6;', 2),
    }
    grand = 0
    for suffix, (loop, nops) in loops.items():
        sub = probe/("probe-"+suffix)
        sub.mkdir()
        text = header + calcs
        text += 'unsigned value(void){unsigned p=0;for(unsigned i=0;i<%d;i++){%s}return p;}\n' % (len(recs), loop)
        data = text.encode()
        (sub/"main.c").write_bytes(data)
        incoming = pack(['cc1','--space-program=result.s','--space-entry=value','--space-memory=65536',
                         '--space-library=libgcc-float.a','-quiet','-O2','-ffreestanding','-fno-builtin','-nostdinc',
                         '-o','result.s','main.c'], {'main.c': data, 'libgcc-float.a': lib.read_bytes()})
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
        expect = struct.pack('<I', len(recs)*nops)
        if d.stdout != expect or d.stderr:
            raise SystemExit(f"{suffix}: OUT mismatch {d.stdout!r} vs {expect!r} err={d.stderr[:200]!r}")
        if (sub/"direct.trace").read_bytes()[-6:] != b' idle\n':
            raise SystemExit(f"{suffix}: direct did not idle")
        ev = {'sub': suffix, 'cases': len(recs), 'operations': nops, 'direct_result': len(recs)*nops,
              'archive_sha256': digest(lib), 'job_sha256': digest(sub/"job.bin"),
              'image_sha256': digest(sub/"image.bin"), 'image_bytes': len(image)}
        (sub/"evidence.json").write_text(json.dumps(ev, indent=2)+"\n")
        print(f"float-{suffix}: direct checks {len(recs)*nops}", flush=True)
        grand += len(recs)*nops
    print(f"Original libgcc float-sf: direct checks {grand}")

if __name__ == "__main__":
    main()
