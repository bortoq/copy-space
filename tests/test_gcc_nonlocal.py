"""Check GCC builtin nonlocal jumps and GNU C nonlocal goto through QEMU.

Native GCC validates the oracle only. Target GCC receives the exact C bytes
through GCCJOB1, and the guest linker returns direct copies. This does not
test libc setjmp, DWARF unwinding, exceptions, or GCC execution inside Space.
"""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from test_gcc_copy_output import decode
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/gcc'))
from job_format import pack_job

CASES={'basic':12,'deep':40,'repeat':35,'arguments':43,'call_after':43,
       'label':47,'label_deep':42}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('image','qemu','artifacts'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--optimization',choices=('O0','O2'),default='O2')
    args=parser.parse_args();root=args.artifacts.resolve();root.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(__file__,root/'run.py');shutil.copyfile(ROOT/'tests/fixtures/gcc/nonlocal.c',root/'nonlocal.c')
    data=(root/'nonlocal.c').read_bytes()
    driver=''.join(f'extern unsigned jump_{n}(void);\n' for n in CASES)
    driver+='int main(void){'+''.join(f'if(jump_{n}()!={v}U)return {i+1};' for i,(n,v) in enumerate(CASES.items()))+'return 0;}\n'
    (root/'native-driver.c').write_text(driver)
    command=['gcc','-'+args.optimization,'-Wall','-Wextra','-Werror',str(root/'nonlocal.c'),
             str(root/'native-driver.c'),'-o',str(root/'native')]
    (root/'native-command.json').write_text(json.dumps(command)+'\n')
    native=subprocess.run(command,capture_output=True);(root/'native.stderr').write_bytes(native.stderr)
    assert native.returncode==0,native.stderr
    native=subprocess.run([str(root/'native')],capture_output=True)
    assert native.returncode==0 and not native.stdout and not native.stderr,native
    flags=['-quiet','-'+args.optimization,'-ffreestanding','-fno-builtin','-nostdinc','-o','result.s','nonlocal.c']
    (root/'compile.job').write_bytes(pack_job(['cc1','--space-result=result.s']+flags,{'nonlocal.c':data}))
    command=[sys.executable,str(ROOT/'scripts/gcc/diagnose_guest.py'),'--image',str(args.image.resolve()),
             '--qemu',str(args.qemu.resolve()),'--job',str(root/'compile.job'),'--artifacts',str(root/'compiler')]
    (root/'compiler-command.json').write_text(json.dumps(command)+'\n');subprocess.run(command,check=True)
    elf=root/'compiler/gcc-diagnostic.elf';emulator=ROOT/'build/bin/space-256m'
    manifest=json.loads((args.image/'image.json').read_text());checks=[]
    for entry,expected in CASES.items():
        folder=root/entry;folder.mkdir()
        job=pack_job(['cc1','--space-program=result.s','--space-entry=jump_'+entry,'--space-memory=65536']+flags,
                     {'nonlocal.c':data});(folder/'job.bin').write_bytes(job)
        command=[str(args.qemu.resolve()),'-strace',str(elf)];(folder/'command.json').write_text(json.dumps(command)+'\n')
        compiled=subprocess.run(command,input=job,capture_output=True,timeout=300)
        (folder/'response.bin').write_bytes(compiled.stdout);(folder/'syscalls.txt').write_bytes(compiled.stderr)
        status,out,err,image=decode(compiled.stdout)
        assert status==compiled.returncode==0 and not out and not err,(entry,err)
        assert len(image)==manifest['copy_program_bytes'];path=folder/'image.bin';path.write_bytes(image)
        command=[str(emulator),'--ticks','10000000','--core',str(path),'--trace-channels',str(folder/'direct.trace')]
        (folder/'direct-command.json').write_text(json.dumps(command)+'\n')
        run=subprocess.run(command,capture_output=True,timeout=300);(folder/'direct.out').write_bytes(run.stdout)
        assert run.returncode==0 and not run.stderr and run.stdout==struct.pack('<I',expected),(entry,run.stdout,run.stderr)
        assert (folder/'direct.trace').read_bytes().endswith(b' idle\n')
        checks.append({'entry':entry,'expected':expected,'image_sha256':digest(path),'job_sha256':digest(folder/'job.bin')})
        print(entry,expected,flush=True)
    (root/'evidence.json').write_text(json.dumps({'scope':__doc__,'optimization':args.optimization,
        'stream_sha256':manifest['stream_sha256'],'elf_sha256':digest(elf),'qemu_sha256':digest(args.qemu),
        'emulator_sha256':digest(emulator),'source_sha256':digest(root/'nonlocal.c'),'checks':checks},indent=2)+'\n')
    print('OK builtin nonlocal jumps:',len(checks),'direct paths',flush=True)


if __name__=='__main__':
    main()
