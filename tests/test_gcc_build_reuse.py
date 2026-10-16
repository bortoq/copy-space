"""Reject unsafe reuse of real GCC build artifacts before copying objects."""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/gcc'))
from build_cc1 import reuse_backend_build


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('base','target','artifacts'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();root=args.artifacts.resolve();root.mkdir(parents=True,exist_ok=False)
    base=args.base.resolve();source=args.target.resolve()/'source'
    before=json.loads((base/'cc1.json').read_text())
    profile=copy.deepcopy(before['build_profile'])
    profile.update(target_source=str(source),target_sources_sha256=json.loads((args.target/'target.json').read_text())['generated_source_sha256'])
    rejected=[]

    def reject(name,changed,base_path=base,source_path=source):
        output=root/('output-'+name)
        try:
            reuse_backend_build(base_path,output,changed,source_path)
        except ValueError as error:
            assert not output.exists(),name
            rejected.append({'case':name,'reason':str(error)})
        else:
            raise AssertionError('accepted unsafe reuse: '+name)

    for key,value in [('compiler','/different/compiler'),('optimization','O0'),('target','another-target')]:
        changed=copy.deepcopy(profile);changed[key]=value;reject(key,changed)
    for name in ('gcc/config/copyspace/copyspace.h','gcc/config/copyspace/copyspace.md'):
        changed=copy.deepcopy(profile);changed['target_sources_sha256'][name]='0'*64
        reject(Path(name).suffix[1:],changed)
    unchanged=copy.deepcopy(profile);unchanged['target_sources_sha256']=copy.deepcopy(before['build_profile']['target_sources_sha256'])
    reject('unchanged-backend',unchanged)
    backend='gcc/config/copyspace/copyspace.cc'
    original=(source/backend).read_text()
    assert original.count('int callee_saved_reg_size;')==1
    for name,text in [('gc-field',original.replace('int callee_saved_reg_size;',
                              'int callee_saved_reg_size; int changed_gc_field;')),
                      ('gc-root',original+'\nstatic GTY(()) tree changed_gc_root;\n')]:
        modified=root/name;path=modified/backend;path.parent.mkdir(parents=True);path.write_text(text)
        changed=copy.deepcopy(profile);changed['target_source']=str(modified)
        changed['target_sources_sha256'][backend]=hashlib.sha256(path.read_bytes()).hexdigest()
        reject(name,changed,source_path=modified)
    damaged=root/'damaged-base';(damaged/'gcc').mkdir(parents=True)
    (damaged/'gcc/cc1').symlink_to(base/'gcc/cc1')
    changed=copy.deepcopy(before);changed['sha256']='0'*64
    (damaged/'cc1.json').write_text(json.dumps(changed))
    (damaged/'build-profile.json').write_text(json.dumps(before['build_profile']))
    reject('compiler-checksum',profile,base_path=damaged)
    changed=copy.deepcopy(before)
    (damaged/'cc1.json').write_text(json.dumps(changed))
    (damaged/'gcc/Makefile').write_text('not the original GCC backend rule\n')
    reject('backend-make-rule',profile,base_path=damaged)
    existing=root/'existing';existing.mkdir();(existing/'sentinel').write_bytes(b'keep')
    try:
        reuse_backend_build(base,existing,profile,source)
    except ValueError:
        assert (existing/'sentinel').read_bytes()==b'keep'
        rejected.append({'case':'existing-output','reason':'preserved existing output'})
    else:
        raise AssertionError('overwrote existing build')
    (root/'evidence.json').write_text(json.dumps({'scope':__doc__,'rejected':rejected},indent=2)+'\n')
    print('OK build reuse:',len(rejected),'unsafe/inconsistent cases rejected without copying')


if __name__=='__main__':
    main()
