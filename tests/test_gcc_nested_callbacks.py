"""Check GNU C nested callbacks across separately compiled target units.

The real target GCC and guest linker run in QEMU. C/header bytes are passed
unchanged through GCCJOB1; only the first guest's assembly is forwarded to
the second. Final programs execute as direct copies. This is not GCC-in-Space
evidence. Native GCC provides a separate oracle, never target assembly.
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

CASES={'capture':17,'modify':61,'array':142,'recursive':15,'void':42,
       'arguments':42,'structure':70,'deep':17,'equal':4,'label':42}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('image','qemu','artifacts'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--optimization',choices=('O0','O2'),default='O2')
    args=parser.parse_args();root=args.artifacts.resolve();root.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(__file__,root/'run.py')
    fixture=ROOT/'tests/fixtures/gcc'
    for name in ('nested_callbacks.c','nested_callback_caller.c','nested_callbacks.h'):
        shutil.copyfile(fixture/name,root/name)
    driver=''.join(f'extern unsigned callback_{n}(void);\n' for n in CASES)
    driver+='int main(void){'+''.join(f'if(callback_{n}()!={v}U)return {i+1};' for i,(n,v) in enumerate(CASES.items()))+'return 0;}\n'
    (root/'native-driver.c').write_text(driver)
    command=['gcc','-'+args.optimization,'-Wall','-Wextra','-Werror',str(root/'nested_callbacks.c'),
             str(root/'nested_callback_caller.c'),str(root/'native-driver.c'),'-o',str(root/'native')]
    (root/'native-command.json').write_text(json.dumps(command)+'\n')
    native=subprocess.run(command,capture_output=True);(root/'native-compile.stderr').write_bytes(native.stderr)
    assert native.returncode==0,native.stderr
    native=subprocess.run([str(root/'native')],capture_output=True)
    assert native.returncode==0 and not native.stdout and not native.stderr,native
    header=(root/'nested_callbacks.h').read_bytes()
    flags=['-quiet','-'+args.optimization,'-ffreestanding','-fno-builtin','-nostdinc','-I.','-o','result.s']
    job=pack_job(['cc1','--space-result=result.s']+flags+['caller.c'],
                 {'caller.c':(root/'nested_callback_caller.c').read_bytes(),'nested_callbacks.h':header})
    (root/'caller.job').write_bytes(job)
    command=[sys.executable,str(ROOT/'scripts/gcc/diagnose_guest.py'),'--image',str(args.image.resolve()),
             '--qemu',str(args.qemu.resolve()),'--job',str(root/'caller.job'),'--artifacts',str(root/'compiler')]
    (root/'compiler-command.json').write_text(json.dumps(command)+'\n');subprocess.run(command,check=True)
    assembly=(root/'compiler/result.bin').read_bytes();(root/'caller.s').write_bytes(assembly)
    elf=root/'compiler/gcc-diagnostic.elf';emulator=ROOT/'build/bin/space-256m'
    manifest=json.loads((args.image/'image.json').read_text());checks=[]
    for entry,expected in CASES.items():
        folder=root/entry;folder.mkdir()
        job=pack_job(['cc1','--space-program=result.s','--space-entry=callback_'+entry,
                      '--space-memory=65536','--space-object=caller.s']+flags+['main.c'],
                     {'main.c':(root/'nested_callbacks.c').read_bytes(),'nested_callbacks.h':header,'caller.s':assembly})
        (folder/'job.bin').write_bytes(job)
        command=[str(args.qemu.resolve()),'-strace',str(elf)]
        (folder/'command.json').write_text(json.dumps(command)+'\n')
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
        'emulator_sha256':digest(emulator),'caller_assembly_sha256':digest(root/'caller.s'),
        'source_sha256':{n:digest(root/n) for n in ('nested_callbacks.c','nested_callback_caller.c','nested_callbacks.h')},
        'checks':checks},indent=2)+'\n')
    print('OK nested callbacks:',len(checks),'entries across separate target units',flush=True)


if __name__=='__main__':
    main()
