"""Verify original freestanding GCC memory routines with actual target GCC.

QEMU runs the compiler and guest linker; results execute as direct copies.
The oracle computes byte patterns and overlap results without memory-library
calls. Native GCC checks the same C tests independently. No host-generated
assembly is forwarded. This is not GCC-in-Space execution evidence.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from test_gcc_libgcc_fixuns import run_one
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/gcc'))
from package_target_library import load_library

CASES={'copy':57,'move':133,'fill':133,'compare':381,'aggregate':4,'builtin':19}


def digest(path):
    with path.open('rb') as s:return hashlib.file_digest(s,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('diagnostic','artifacts'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--unit-run',type=Path,action='append',required=True)
    parser.add_argument('--image',type=Path)
    parser.add_argument('--library',type=Path)
    args=parser.parse_args();root=args.artifacts.resolve();root.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(__file__,root/'run.py')
    shutil.copyfile(ROOT/'tests/test_gcc_libgcc_fixuns.py',root/'run-helper.py')
    source=(ROOT/'tests/fixtures/gcc/memory_runtime.c').read_bytes();(root/'main.c').write_bytes(source)
    driver=''.join(f'extern unsigned {n}_checks(void);\n' for n in CASES)
    driver+='int main(void){'+''.join(f'if({n}_checks()!={v}U)return {i+1};' for i,(n,v) in enumerate(CASES.items()))+'return 0;}\n'
    (root/'native-driver.c').write_text(driver)
    command=['gcc','-O2','-Wall','-Wextra','-Werror','-ffreestanding','-fno-builtin',str(root/'main.c'),str(root/'native-driver.c'),'-o',str(root/'native')]
    (root/'native-command.json').write_text(json.dumps(command)+'\n')
    run=subprocess.run(command,capture_output=True);assert run.returncode==0,run.stderr
    run=subprocess.run([str(root/'native')],capture_output=True);assert run.returncode==0,run
    library=root/'memory.a';members=[];hashes={}
    producers={}
    for run in args.unit_run:
        for record in json.loads((run/'evidence.json').read_text())['units']:
            assert record['unit'] not in producers
            producers[record['unit']]=run/record['unit']
    assert set(producers)=={'memcpy','memmove','memset','memcmp'}
    for unit,folder in producers.items():
        record=json.loads((folder/'evidence.json').read_text());src=folder/'assembly.s'
        assert record['code']==record['process_exit']==0 and digest(src)==record['assembly_sha256']
        dest=root/(unit+'.s');shutil.copyfile(src,dest);members.append(str(dest));hashes[unit]=digest(src)
    command=['ar','rcSD',str(library)]+members;(root/'archive-command.json').write_text(json.dumps(command)+'\n')
    subprocess.run(command,capture_output=True,check=True)
    diag=args.diagnostic.resolve();prior=json.loads((diag/'evidence.json').read_text());elf=diag/'gcc-diagnostic.elf'
    qemu=Path(json.loads((diag/'command.json').read_text())[0]);assert digest(elf)==prior['elf_sha256'] and digest(qemu)==prior['qemu_sha256']
    installed=bool(args.image)
    if installed:
        assert args.library
        archive,receipt=load_library(args.library.resolve());prepared=json.loads((args.image/'image.json').read_text())
        assert prepared['elf_sha256']==prior['original_elf_sha256']
        assert prepared['target_library']['archive_sha256']==digest(archive)==receipt['archive_sha256']
    emulator=ROOT/'build/bin/space-256m';checks=[]
    for name,count in CASES.items():
        # run_one uses value as the entry; forwarding calls retain noipa bodies.
        text=source+f'\nunsigned value(void){{return {name}_checks();}}\n'.encode()
        result=run_one(qemu,elf,emulator,library.read_bytes(),'memory.a',text,root/name,count,installed=installed)
        checks.append(dict(entry=name,**result));print(name,count,flush=True)
    (root/'evidence.json').write_text(json.dumps({'scope':__doc__,'elf_sha256':digest(elf),
        'qemu_sha256':digest(qemu),'emulator_sha256':digest(emulator),'source_sha256':digest(root/'main.c'),
        'archive_sha256':digest(library),'members_sha256':hashes,'installed':installed,'checks':checks},indent=2)+'\n')


if __name__=='__main__':
    main()
