"""Check original trapping libgcc arithmetic with real target GCC in QEMU.

Ordinary +, -, *, and unary - compile with -ftrapv; abs checks call the typed
libgcc entry explicitly. A test-owned abort terminates through __builtin_trap.
This does not supply a target libc abort. Final programs execute direct copies;
QEMU compiler execution is not evidence of GCC execution inside Space.
"""
import argparse
import hashlib
import json
import random
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from test_gcc_copy_output import decode
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/gcc'))
from job_format import pack_job
from package_target_library import load_library

UNITS = ('addvsi3', 'addvdi3', 'subvsi3', 'subvdi3', 'mulvsi3', 'mulvdi3',
         'negvsi2', 'negvdi2', 'absvsi2', 'absvdi2')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def source(width):
    low, high = -(1 << (width-1)), (1 << (width-1))-1
    mask = (1 << width)-1
    rng = random.Random(0xf7a9+width)
    edges = (0, 1, -1, 2, -2, low, low+1, high-1, high)
    pairs = [(a,b) for a in edges for b in edges]
    pairs += [(rng.randint(low,high),rng.randint(low,high)) for _ in range(40)]
    # Full-width random products almost always overflow. Include balanced and
    # unbalanced factors whose multiword products are representable as well.
    pairs += [(rng.randrange(-(1 << (width//2-2)), 1 << (width//2-2)),
               rng.randrange(-(1 << (width//2-2)), 1 << (width//2-2))) for _ in range(40)]
    pairs += [(rng.randrange(-(1 << (width-12)), 1 << (width-12)),
               rng.randrange(-512,512)) for _ in range(40)]
    rows, count = [], 0
    for a,b in pairs:
        values = (a+b,a-b,a*b,-a,abs(a))
        valid = sum(1 << i for i,v in enumerate(values) if low <= v <= high)
        count += valid.bit_count()
        rows.append('{'+','.join(str(v & mask)+'ULL' for v in (a,b))+', {'+
                    ','.join(str(v & mask)+'ULL' for v in values)+'},'+str(valid)+'U}')
    name = 'si2' if width == 32 else 'di2'
    text = (f'typedef __INT{width}_TYPE__ T;typedef __UINT{width}_TYPE__ U;\n'
            '__attribute__((__noreturn__)) void abort(void){__builtin_trap();}\n'
            f'extern T __absv{name}(T);\n'
            '#define FN static __attribute__((__noinline__,__noipa__))\n'
            'FN T add(T a,T b){return a+b;}\nFN T sub(T a,T b){return a-b;}\n'
            'FN T mul(T a,T b){return a*b;}\nFN T neg(T a){return -a;}\n'
            f'FN T absolute(T a){{return __absv{name}(a);}}\n'
            'struct row{U a,b,r[5];unsigned valid;};static const struct row cases[]={')
    # Use braces around the result array; all constants are unsigned bit patterns.
    text += ','.join(rows)+'};\n'
    text += 'unsigned value(void){unsigned p=0;for(unsigned j=0;j<'+str(len(pairs))+';j++){const struct row *r=cases+j;'
    for i,expr in enumerate(('add((T)r->a,(T)r->b)', 'sub((T)r->a,(T)r->b)',
                             'mul((T)r->a,(T)r->b)', 'neg((T)r->a)', 'absolute((T)r->a)')):
        text += f'if(r->valid&{1 << i}U)p+=(U){expr}==r->r[{i}];'
    text += '}return p;}\n'
    traps = {'add_high': ('add',high,1), 'add_low': ('add',low,-1),
             'sub_low': ('sub',low,1), 'sub_high': ('sub',high,-1),
             'mul_high': ('mul',high,2), 'mul_low': ('mul',low,-1),
             'mul_high_words': ('mul',1 << (width//2),1 << (width//2)),
             'mul_negative': ('mul',low,2),
             'neg_low': ('neg',low,None), 'abs_low': ('absolute',low,None)}
    for name,(op,a,b) in traps.items():
        text += f'unsigned {name}(void){{volatile U a={a & mask}ULL;'
        if b is not None:
            text += f'volatile U b={b & mask}ULL;return (unsigned){op}((T)a,(T)b);}}\n'
        else:
            text += f'return (unsigned){op}((T)a);}}\n'
    return text.encode(), count, list(traps)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('units','target-library','diagnostic','artifacts'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--image',type=Path,help='verify and use the installed archive for positive cases')
    args = parser.parse_args()
    root = args.artifacts.resolve(); root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, root/'run.py')
    archive, receipt = load_library(args.target_library.resolve())
    library = root/'libgcc.a'; shutil.copyfile(archive, library)
    members, hashes = [], {}
    for unit in UNITS:
        src = args.units.resolve()/unit/'assembly.s'
        r = json.loads((src.parent/'evidence.json').read_text())
        assert r['code'] == r['process_exit'] == 0 and digest(src) == r['assembly_sha256']
        dst = root/(unit+'.s'); shutil.copyfile(src,dst); members.append(str(dst)); hashes[unit] = digest(src)
    cmd = ['ar','rSD',str(library)]+members
    (root/'archive-command.json').write_text(json.dumps(cmd)+'\n')
    subprocess.run(cmd, capture_output=True, check=True)
    diag = args.diagnostic.resolve(); elf = diag/'gcc-diagnostic.elf'
    prior = json.loads((diag/'evidence.json').read_text())
    qemu = Path(json.loads((diag/'command.json').read_text())[0])
    assert digest(elf) == prior['elf_sha256'] and digest(qemu) == prior['qemu_sha256']
    if args.image:
        image_root = args.image.resolve()
        prepared = json.loads((image_root/'image.json').read_text())
        assert digest(image_root/'gcc-space.elf') == prepared['elf_sha256'] == prior['original_elf_sha256']
        assert digest(library) == receipt['archive_sha256'] == prepared['target_library']['archive_sha256']
    emulator = ROOT/'build/bin/space-256m'

    def compile_job(folder, argv, files):
        folder.mkdir()
        job = pack_job(argv,files); (folder/'job.bin').write_bytes(job)
        cmd = [str(qemu),'-strace',str(elf)]
        (folder/'command.json').write_text(json.dumps(cmd)+'\n')
        run = subprocess.run(cmd,input=job,capture_output=True,timeout=300)
        (folder/'response.bin').write_bytes(run.stdout); (folder/'syscalls.txt').write_bytes(run.stderr)
        status,out,err,result = decode(run.stdout)
        assert run.returncode == status and not out
        return status,err,result

    checks = []
    for width in (32,64):
        folder = root/str(width); folder.mkdir()
        data,count,traps = source(width); (folder/'main.c').write_bytes(data)
        flags = ['-quiet','-O2','-ftrapv','-ffreestanding','-fno-builtin','-nostdinc','-o','result.s','main.c']
        status,err,assembly = compile_job(folder/'compile',['cc1','--space-result=result.s']+flags, {'main.c':data})
        assert status == 0 and not err and assembly
        (folder/'calcs.s').write_bytes(assembly)
        for entry in ['missing','value']+traps:
            selected = 'value' if entry == 'missing' else entry
            options = [] if args.image else ['--space-library=libgcc.a']
            files = {'main.c':b'void unused(void){}\n','calcs.s':assembly}
            if entry == 'missing':
                options = ['--space-no-libgcc']
            elif not args.image:
                files['libgcc.a'] = library.read_bytes()
            argv = ['cc1','--space-program=result.s','--space-entry='+selected,'--space-memory=65536',
                    '--space-object=calcs.s']+options+flags
            status,err,image = compile_job(folder/entry,argv,files)
            if entry == 'missing':
                assert status == 126 and b'undefined' in err and not image
                checks.append({'width':width,'entry':entry,'exit':status}); continue
            assert status == 0 and not err and image, (width,entry,err)
            path = folder/entry/'image.bin'; path.write_bytes(image)
            cmd = [str(emulator),'--ticks','10000000','--core',str(path),
                   '--trace-channels',str(folder/entry/'direct.trace')]
            (folder/entry/'direct-command.json').write_text(json.dumps(cmd)+'\n')
            run = subprocess.run(cmd,capture_output=True,timeout=300)
            (folder/entry/'direct.out').write_bytes(run.stdout)
            assert run.returncode == 0 and not run.stderr
            expected = struct.pack('<I',count) if entry == 'value' else b''
            assert run.stdout == expected, (width,entry,run.stdout,expected)
            assert (folder/entry/'direct.trace').read_bytes().endswith(b' idle\n')
            checks.append({'width':width,'entry':entry,'checks':count if entry == 'value' else 1,
                           'input_files':list(files),'image_sha256':digest(path),'job_sha256':digest(folder/entry/'job.bin')})
            print(width,entry,'passed',count if entry == 'value' else 'idle without OUT',flush=True)
    (root/'evidence.json').write_text(json.dumps({'scope':__doc__,'elf_sha256':digest(elf),
        'qemu_sha256':digest(qemu),'emulator_sha256':digest(emulator),'archive_sha256':digest(library),
        'base_archive_sha256':receipt['archive_sha256'],'installed':bool(args.image),
        'input_assembly_sha256':hashes,'checks':checks},indent=2)+'\n')


if __name__ == '__main__':
    main()
