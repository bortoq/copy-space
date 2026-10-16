"""Link single-hart __sync_* helpers and execute direct copies.

The fixture or installed project runtime implements the fifteen _4 and
fifteen _8 read-modify-write/CAS helpers as plain volatile accesses plus
a compiler barrier (correct only on one hart with sequential copies;
no SMP claim; nand uses post-GCC-4.4 semantics verified against native
GCC). Plain atomic load/store, lock_release and synchronize need no
out-of-line helper. Guards: validate inputs, check every
subprocess/file syscall, verify Python reference before asserting
direct OUT. QEMU diagnostic only. Each probe resets its cell per case
and checks both the return value and the final cell contents.
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

OPS = {
    'add': lambda a, b, m: (a + b) & m,
    'sub': lambda a, b, m: (a - b) & m,
    'or': lambda a, b, m: a | b,
    'and': lambda a, b, m: a & b,
    'xor': lambda a, b, m: a ^ b,
    'nand': lambda a, b, m: (~(a & b)) & m,
}

def digest(path, algo="sha256"):
    if not path.is_file():
        raise SystemExit(f"missing file: {path}")
    with path.open("rb") as s:
        return hashlib.file_digest(s, algo).hexdigest()

def run_probe(qemu, elf, emu, lib_bytes, lib_name, main_c, sub, expect):
    if not main_c or (lib_bytes is not None and not lib_bytes):
        raise SystemExit("empty harness or library")
    sub.mkdir(parents=True, exist_ok=False)
    (sub/"main.c").write_bytes(main_c)
    files = {'main.c': main_c}
    library_option = []
    if lib_bytes is not None:
        files[lib_name] = lib_bytes
        library_option = ['--space-library='+lib_name]
    incoming = pack(['cc1','--space-program=result.s','--space-entry=value','--space-memory=65536']+
                   library_option+['-quiet','-O2','-ffreestanding','-fno-builtin','-nostdinc',
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
    notes = [line for line in stderr.split(b'\n') if b'warning:' in line or b'error:' in line]
    if not (code == 0 and not stdout and not notes and image):
        raise SystemExit(f"bad GCCOUT1 code={code} stderr={stderr[:400]!r}")
    (sub/"image.bin").write_bytes(image)
    cmd2 = [str(emu),'--ticks','10000000','--core',str(sub/"image.bin"),
            '--trace-channels',str(sub/"direct.trace")]
    (sub/"direct-command.json").write_text(json.dumps(cmd2)+"\n")
    d = subprocess.run(cmd2, capture_output=True, timeout=300)
    (sub/"direct.out").write_bytes(d.stdout)
    if d.returncode != 0:
        raise SystemExit(f"direct failed {d.returncode} {d.stderr[:300]!r}")
    want = struct.pack('<I', expect)
    if d.stdout != want or d.stderr:
        raise SystemExit(f"OUT mismatch {d.stdout!r} vs {want!r} err={d.stderr[:200]!r}")
    if (sub/"direct.trace").read_bytes()[-6:] != b' idle\n':
        raise SystemExit("direct did not idle")
    (sub/"evidence.json").write_text(json.dumps({'direct_result': expect, 'input_files': list(files),
        'installed_runtime': lib_bytes is None, 'job_sha256': digest(sub/'job.bin'),
        'image_sha256': digest(sub/'image.bin')}, indent=2)+"\n")
    return expect

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    runtime = parser.add_mutually_exclusive_group(required=True)
    runtime.add_argument('--sync-assembly', type=Path,
                        help='assembly.s compiled from sync_up.c by the target cc1')
    runtime.add_argument('--installed', action='store_true', help='use the runtime installed in --image; send C only')
    parser.add_argument('--image', type=Path)
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=0x57c)
    args = parser.parse_args()
    asm = args.sync_assembly.resolve() if args.sync_assembly else None
    if asm is not None and (not asm.is_file() or asm.stat().st_size == 0):
        raise SystemExit("missing sync assembly")
    diag = args.diagnostic.resolve()
    elf = diag/"gcc-diagnostic.elf"
    prior = json.loads((diag/"evidence.json").read_text())
    if not elf.is_file() or digest(elf) != prior['elf_sha256']:
        parser.error('changed diagnostic ELF')
    qemu = Path(json.loads((diag/"command.json").read_text())[0])
    if not qemu.is_file() or digest(qemu) != prior['qemu_sha256']:
        parser.error('changed diagnostic qemu')
    installed_hash = None
    if args.installed:
        if not args.image:
            parser.error('--installed requires --image')
        image = args.image.resolve()
        manifest = json.loads((image/'image.json').read_text())
        assert prior['original_elf_sha256'] == manifest['elf_sha256'] == digest(image/'gcc-space.elf')
        assert manifest['target_library']['default']
        installed_hash = digest(image/'target-libgcc.a')
        assert installed_hash == manifest['target_library']['archive_sha256']
    emu = ROOT/"build/bin/space-256m"
    if not emu.is_file():
        raise SystemExit(f"missing emulator {emu}")
    probe = args.artifacts.resolve()
    probe.mkdir(parents=True, exist_ok=False)
    import shutil
    shutil.copyfile(__file__, probe/'run.py')
    libb = None
    if asm is not None:
        (probe/"sync_up.s").write_bytes(asm.read_bytes())
        lib = probe/"libsync.a"
        r = subprocess.run(["ar","rcSD",str(lib),str(probe/"sync_up.s")], capture_output=True)
        if r.returncode != 0:
            raise SystemExit(f"ar failed: {r.stderr[:500]}")
        libb = lib.read_bytes()
    rng = random.Random(args.seed)
    M32 = (1 << 32) - 1
    M64 = (1 << 64) - 1
    edge32 = [0, 1, 2, 3, 0x7fffffff, 0x80000000, 0xfffffffe, 0xffffffff, 0x12345678, 0xdeadbeef]
    pairs32 = [(a, b) for a, b in zip(edge32, reversed(edge32))]
    pairs32 += [(rng.getrandbits(32), rng.getrandbits(32)) for _ in range(50)]
    edge64 = [0, 1, 2, 3, 0x7fffffffffffffff, 0x8000000000000000,
              0xfffffffffffffffe, 0xffffffffffffffff, 0x123456789abcdef, 0xdeadbeefcafebabe]
    pairs64 = [(a, b) for a, b in zip(edge64, reversed(edge64))]
    pairs64 += [(rng.getrandbits(64), rng.getrandbits(64)) for _ in range(50)]
    assert len(pairs32) == len(pairs64) == 60
    grand = 0
    # probe-a: six _4 fetch ops; check return and final cell
    names = ['add', 'sub', 'or', 'and', 'xor', 'nand']
    # per-op expectations differ, so emit one table per op instead
    text = ('typedef __UINT32_TYPE__ u32;\n'
            + ''.join(f'unsigned __sync_fetch_and_{n}_4(volatile void*,unsigned);\n' for n in names)
            + 'static u32 cell;\n')
    for i, n in enumerate(names):
        text += f'struct rec{i} {{ u32 init,arg,eret,efinal; }};\n'
        text += f'static const struct rec{i} cases{i}[]={{'
        for a, b in pairs32:
            text += '{%dU,%dU,%dU,%dU},' % (a, b, a, OPS[n](a, b, M32))
        text += '};\n'
    for i, n in enumerate(names):
        text += (f'static __attribute__((__noinline__,__noipa__)) unsigned c{i}(void){{unsigned p=0;'
                 f'for(unsigned k=0;k<{len(pairs32)};k++){{cell=cases{i}[k].init;'
                 f'u32 r=__sync_fetch_and_{n}_4(&cell,cases{i}[k].arg);'
                 f'p+=(r==cases{i}[k].eret)+(cell==cases{i}[k].efinal);}}return p;}}\n')
    text += 'unsigned value(void){return %s;}\n' % '+'.join(f'c{i}()' for i in range(len(names)))
    n = run_probe(qemu, elf, emu, libb, "libsync.a", text.encode(), probe/"probe-a", len(pairs32)*2*len(names))
    print(f"sync-a: direct checks {n}", flush=True)
    grand += n
    # probe-b: six _4 update ops + bool/val CAS + test_and_set
    unames = ['add', 'sub', 'or', 'and', 'xor', 'nand']
    text = ('typedef __UINT32_TYPE__ u32;\n'
            + ''.join(f'unsigned __sync_{n}_and_fetch_4(volatile void*,unsigned);\n' for n in unames)
            + '_Bool __sync_bool_compare_and_swap_4(volatile void*,unsigned,unsigned);\n'
              'unsigned __sync_val_compare_and_swap_4(volatile void*,unsigned,unsigned);\n'
              'unsigned __sync_lock_test_and_set_4(volatile void*,unsigned);\nstatic u32 cell;\n')
    for i, n in enumerate(unames):
        text += f'struct urec{i} {{ u32 init,arg,e; }};\nstatic const struct urec{i} ucases{i}[]={{'
        for a, b in pairs32:
            text += '{%dU,%dU,%dU},' % (a, b, OPS[n](a, b, M32))
        text += '};\n'
    text += 'struct crec { u32 init,old,new,eret,efinal; };\nstatic const struct crec ccases[]={'
    for k in range(60):
        init = pairs32[k][0]
        old = init if k % 2 == 0 else (init ^ 0x5a5a5a5a) & M32
        new = pairs32[k][1]
        hit = 1 if old == init else 0
        text += '{%dU,%dU,%dU,%dU,%dU},' % (init, old, new, hit, new if hit else init)
    text += '};\nstruct trec { u32 init,arg; };\nstatic const struct trec tcases[]={'
    for a, b in pairs32:
        text += '{%dU,%dU},' % (a, b)
    text += '};\n'
    for i, n in enumerate(unames):
        text += (f'static __attribute__((__noinline__,__noipa__)) unsigned u{i}(void){{unsigned p=0;'
                 f'for(unsigned k=0;k<60;k++){{cell=ucases{i}[k].init;'
                 f'u32 r=__sync_{n}_and_fetch_4(&cell,ucases{i}[k].arg);'
                 f'p+=(r==ucases{i}[k].e)+(cell==ucases{i}[k].e);}}return p;}}\n')
    text += ('static __attribute__((__noinline__,__noipa__)) unsigned cb(void){unsigned p=0;'
             'for(unsigned k=0;k<60;k++){cell=ccases[k].init;'
             'unsigned r=__sync_bool_compare_and_swap_4(&cell,ccases[k].old,ccases[k].new);'
             'p+=(r==ccases[k].eret)+(cell==ccases[k].efinal);}return p;}\n')
    text += ('static __attribute__((__noinline__,__noipa__)) unsigned cv(void){unsigned p=0;'
             'for(unsigned k=0;k<60;k++){cell=ccases[k].init;'
             'u32 r=__sync_val_compare_and_swap_4(&cell,ccases[k].old,ccases[k].new);'
             'p+=(r==ccases[k].init)+(cell==ccases[k].efinal);}return p;}\n')
    text += ('static __attribute__((__noinline__,__noipa__)) unsigned ct(void){unsigned p=0;'
             'for(unsigned k=0;k<60;k++){cell=tcases[k].init;'
             'u32 r=__sync_lock_test_and_set_4(&cell,tcases[k].arg);'
             'p+=(r==tcases[k].init)+(cell==tcases[k].arg);}return p;}\n')
    text += 'unsigned value(void){return %s;}\n' % '+'.join([f'u{i}()' for i in range(6)] + ['cb()', 'cv()', 'ct()'])
    n = run_probe(qemu, elf, emu, libb, "libsync.a", text.encode(), probe/"probe-b", (60*2*6)+(60*2*3))
    print(f"sync-b: direct checks {n}", flush=True)
    grand += n
    # probe-c: fifteen _8 ops (six fetch + six update + bool/val CAS + test_and_set)
    text = ('typedef __UINT64_TYPE__ u64;\n'
            + ''.join(f'unsigned long long __sync_fetch_and_{n}_8(volatile void*,unsigned long long);\n' for n in unames)
            + ''.join(f'unsigned long long __sync_{n}_and_fetch_8(volatile void*,unsigned long long);\n' for n in unames)
            + '_Bool __sync_bool_compare_and_swap_8(volatile void*,unsigned long long,unsigned long long);\n'
              'unsigned long long __sync_val_compare_and_swap_8(volatile void*,unsigned long long,unsigned long long);\n'
              'unsigned long long __sync_lock_test_and_set_8(volatile void*,unsigned long long);\nstatic u64 cell;\n')
    text += 'struct r8 { u64 init,arg; };\nstatic const struct r8 cases8[]={'
    for a, b in pairs64:
        text += '{%dULL,%dULL},' % (a, b)
    text += '};\nstruct c8 { u64 init,old,new; };\nstatic const struct c8 ccases8[]={'
    for k in range(60):
        init = pairs64[k][0]
        old = init if k % 2 == 0 else (init ^ 0x5a5a5a5a5a5a5a5a) & M64
        text += '{%dULL,%dULL,%dULL},' % (init, old, pairs64[k][1])
    text += '};\n'
    for i, n in enumerate(unames):
        text += (f'static __attribute__((__noinline__,__noipa__)) unsigned f{i}(void){{unsigned p=0;'
                 f'for(unsigned k=0;k<60;k++){{cell=cases8[k].init;'
                 f'u64 r=__sync_fetch_and_{n}_8(&cell,cases8[k].arg);'
                 f'u64 e=cases8[k].init; u64 f=({op_expr(n, "cases8[k].init", "cases8[k].arg")});'
                 f'p+=(r==e)+(cell==f);}}return p;}}\n')
    for i, n in enumerate(unames):
        text += (f'static __attribute__((__noinline__,__noipa__)) unsigned g{i}(void){{unsigned p=0;'
                 f'for(unsigned k=0;k<60;k++){{cell=cases8[k].init;'
                 f'u64 r=__sync_{n}_and_fetch_8(&cell,cases8[k].arg);'
                 f'u64 e=({op_expr(n, "cases8[k].init", "cases8[k].arg")});'
                 f'p+=(r==e)+(cell==e);}}return p;}}\n')
    text += ('static __attribute__((__noinline__,__noipa__)) unsigned hb(void){unsigned p=0;'
             'for(unsigned k=0;k<60;k++){cell=ccases8[k].init;'
             'unsigned r=__sync_bool_compare_and_swap_8(&cell,ccases8[k].old,ccases8[k].new);'
             'unsigned e=(ccases8[k].old==ccases8[k].init);'
             'u64 f=e?ccases8[k].new:ccases8[k].init;p+=(r==e)+(cell==f);}return p;}\n')
    text += ('static __attribute__((__noinline__,__noipa__)) unsigned hv(void){unsigned p=0;'
             'for(unsigned k=0;k<60;k++){cell=ccases8[k].init;'
             'u64 r=__sync_val_compare_and_swap_8(&cell,ccases8[k].old,ccases8[k].new);'
             'u64 f=(ccases8[k].old==ccases8[k].init)?ccases8[k].new:ccases8[k].init;'
             'p+=(r==ccases8[k].init)+(cell==f);}return p;}\n')
    text += ('static __attribute__((__noinline__,__noipa__)) unsigned ht(void){unsigned p=0;'
             'for(unsigned k=0;k<60;k++){cell=cases8[k].init;'
             'u64 r=__sync_lock_test_and_set_8(&cell,cases8[k].arg);'
             'p+=(r==cases8[k].init)+(cell==cases8[k].arg);}return p;}\n')
    text += 'unsigned value(void){return %s;}\n' % '+'.join(
        [f'f{i}()' for i in range(6)] + [f'g{i}()' for i in range(6)] + ['hb()', 'hv()', 'ht()'])
    n = run_probe(qemu, elf, emu, libb, "libsync.a", text.encode(), probe/"probe-c", 60*2*15)
    print(f"sync-c: direct checks {n}", flush=True)
    grand += n
    (probe/'evidence.json').write_text(json.dumps({'scope': __doc__, 'checks': grand,
        'installed_runtime': args.installed, 'installed_archive_sha256': installed_hash,
        'compiler_elf_sha256': prior['elf_sha256'], 'qemu_sha256': prior['qemu_sha256'],
        'emulator_sha256': digest(emu)}, indent=2)+'\n')
    print(f"Single-hart sync helpers: direct checks {grand}")

def op_expr(name, a, b):
    return {'add': f'({a}+{b})', 'sub': f'({a}-{b})', 'or': f'({a}|{b})',
            'and': f'({a}&{b})', 'xor': f'({a}^{b})',
            'nand': f'(~({a}&{b}))'}[name]

if __name__ == "__main__":
    main()
