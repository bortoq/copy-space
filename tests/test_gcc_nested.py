"""Check GNU C static chains with real GCC and guest lowering in QEMU.

Eight ordinary C entries execute as direct copies. Native GCC only checks the
test oracle; its assembly is never forwarded to the target. Older compiler
images reject nested function addresses; --function-descriptors checks that
new images accept and execute them. This is not GCC-in-Space evidence.
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

CASES={'direct':17,'modify':47,'recursive':15,'siblings':26,'deep':17,
       'arguments':42,'variadic':41,'address':43}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('image','qemu','artifacts'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--optimization',choices=('O0','O2'),default='O2')
    parser.add_argument('--function-descriptors',action='store_true')
    args=parser.parse_args()
    root=args.artifacts.resolve();root.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(__file__,root/'run.py')
    data=(ROOT/'tests/fixtures/gcc/nested.c').read_bytes();(root/'nested.c').write_bytes(data)
    manifest=json.loads((args.image/'image.json').read_text())
    assert digest(args.image/'gcc-space.elf')==manifest['elf_sha256']
    driver=''.join(f'extern unsigned {entry}(void);\n' for entry in CASES)
    driver+='int main(void){'+''.join(f'if({entry}()!={expected}U)return 1;' for entry,expected in CASES.items())+'return 0;}\n'
    (root/'native-driver.c').write_text(driver)
    command=['gcc','-'+args.optimization,'-Wall','-Wextra','-Werror',str(root/'nested.c'),str(root/'native-driver.c'),'-o',str(root/'native')]
    (root/'native-command.json').write_text(json.dumps(command)+'\n')
    native=subprocess.run(command,capture_output=True);assert native.returncode==0,native.stderr
    native=subprocess.run([str(root/'native')],capture_output=True)
    assert native.returncode==0 and not native.stdout and not native.stderr
    flags=['-quiet','-'+args.optimization,'-ffreestanding','-fno-builtin','-nostdinc','-o','result.s','nested.c']
    incoming=pack_job(['cc1','--space-result=result.s']+flags,{'nested.c':data})
    (root/'compile.job').write_bytes(incoming)
    command=[sys.executable,str(ROOT/'scripts/gcc/diagnose_guest.py'),'--image',str(args.image.resolve()),
             '--qemu',str(args.qemu.resolve()),'--job',str(root/'compile.job'),'--artifacts',str(root/'compiler')]
    (root/'compiler-command.json').write_text(json.dumps(command)+'\n')
    subprocess.run(command,check=True)
    elf=root/'compiler/gcc-diagnostic.elf';emulator=ROOT/'build/bin/space-256m'
    checks=[]
    for entry,expected in CASES.items():
        folder=root/entry;folder.mkdir()
        incoming=pack_job(['cc1','--space-program=result.s','--space-entry='+entry,'--space-memory=65536']+flags,
                          {'nested.c':data})
        (folder/'job.bin').write_bytes(incoming)
        command=[str(args.qemu.resolve()),'-strace',str(elf)]
        (folder/'command.json').write_text(json.dumps(command)+'\n')
        compiled=subprocess.run(command,input=incoming,capture_output=True,timeout=300)
        (folder/'response.bin').write_bytes(compiled.stdout);(folder/'syscalls.txt').write_bytes(compiled.stderr)
        status,out,err,image=decode(compiled.stdout)
        assert status==compiled.returncode==0 and not out and not err,err
        assert len(image)==manifest['copy_program_bytes']
        path=folder/'image.bin';path.write_bytes(image)
        command=[str(emulator),'--ticks','10000000','--core',str(path),'--trace-channels',str(folder/'direct.trace')]
        (folder/'direct-command.json').write_text(json.dumps(command)+'\n')
        run=subprocess.run(command,capture_output=True,timeout=300)
        (folder/'direct.out').write_bytes(run.stdout)
        assert run.returncode==0 and not run.stderr and run.stdout==struct.pack('<I',expected),(entry,run.stdout)
        assert (folder/'direct.trace').read_bytes().endswith(b' idle\n')
        checks.append({'entry':entry,'result':expected,'image_sha256':digest(path),'job_sha256':digest(folder/'job.bin')})
        print(entry,expected,flush=True)
    negative=b'__attribute__((noinline,noipa)) unsigned invoke(unsigned(*fn)(unsigned)){return fn(7);}\nunsigned value(void){volatile unsigned bias=10; unsigned nested(unsigned x){return bias+x;} return invoke(nested);}\n'
    (root/'trampoline.c').write_bytes(negative)
    incoming=pack_job(['cc1','--space-program=result.s','--space-entry=value','-quiet','-O2','-ffreestanding',
                      '-fno-builtin','-nostdinc','-o','result.s','trampoline.c'],{'trampoline.c':negative})
    (root/'trampoline.job').write_bytes(incoming)
    run=subprocess.run([str(args.qemu.resolve()),'-strace',str(elf)],input=incoming,capture_output=True,timeout=300)
    (root/'trampoline.response').write_bytes(run.stdout);(root/'trampoline.syscalls').write_bytes(run.stderr)
    status,out,err,image=decode(run.stdout)
    assert status==run.returncode and not out
    if args.function_descriptors:
        assert status==0 and not err and len(image)==manifest['copy_program_bytes'],err
        path=root/'callback.bin';path.write_bytes(image)
        command=[str(emulator),'--ticks','10000000','--core',str(path),
                 '--trace-channels',str(root/'callback.trace')]
        (root/'callback-command.json').write_text(json.dumps(command)+'\n')
        checked=subprocess.run(command,capture_output=True,timeout=300)
        (root/'callback.out').write_bytes(checked.stdout)
        assert checked.returncode==0 and not checked.stderr and checked.stdout==struct.pack('<I',17)
        assert (root/'callback.trace').read_bytes().endswith(b' idle\n')
    else:
        assert status and not image
        assert b'nested-function trampolines are not implemented' in err
    (root/'evidence.json').write_text(json.dumps({'scope':__doc__,'stream_sha256':manifest['stream_sha256'],
        'optimization':args.optimization,'source_sha256':digest(root/'nested.c'),'elf_sha256':digest(elf),'qemu_sha256':digest(args.qemu),
        'emulator_sha256':digest(emulator),'checks':checks,
        'trampoline_rejected':not args.function_descriptors,'function_descriptors':args.function_descriptors},indent=2)+'\n')
    print('OK static chains:',len(checks),'direct GNU C entries; descriptor callback',
          'passed' if args.function_descriptors else 'rejected by old compiler',flush=True)


if __name__=='__main__':
    main()
