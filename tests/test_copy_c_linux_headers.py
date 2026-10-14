"""Verify pinned Linux headers with the explicit copy-space compiler port."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
base=Path(__file__).resolve().parents[1];sys.path.insert(0,str(base/'scripts/copy_c'))
sys.path.insert(0,str(base/'tests'))
from space_segments import execute_segments
parser=argparse.ArgumentParser(description='Verify the pinned Linux compiler header port and direct-copy output.')
parser.add_argument('--source-root',type=Path,required=True)
parser.add_argument('--artifacts',type=Path,required=True)
parser.add_argument('--native-only',action='store_true')
options=parser.parse_args()
from job import pack_files
root=options.artifacts.resolve();root.mkdir(parents=True,exist_ok=False)
original=options.source_root.resolve()
pinned={
 'include/linux/compiler_types.h':'8a3c9ffa750209298e1cd1092f5362033cd3c220e9dc57ddcd3dc4613c0c9ef9',
 'include/linux/compiler_attributes.h':'4a09434134581e394326c25a884061a15d88a79ba2f1a1a86f329c6b17836cb9',
 'include/linux/compiler-gcc.h':'016dbe4972cc306b8fe671e1684af1458f81acb7519254af8cb9d704629b788a',
}
source=b'#define __KERNEL__ 1\n#include <linux/compiler_types.h>\n_Static_assert(__same_type((unsigned long)0,typeof(((struct ftrace_branch_data*)0)->correct)),"type");\nint main(){struct ftrace_branch_data b={.correct=3,.incorrect=4};return b.miss+b.hit;}\n'
(root/'main.c').write_bytes(source)
original_hashes={}
for name in ['include/linux/compiler_types.h','include/linux/compiler_attributes.h','include/linux/compiler-gcc.h']:
 content=(original/name).read_bytes();sig=hashlib.sha256(content).hexdigest();assert sig==pinned[name]
 original_hashes[name]=sig
 for dest in [root/name,root/'original'/name]:
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(content)
patch=root/'compiler-identification.patch';patch.write_bytes((base/'runtime/linux/patches/0001-copyspace-compiler-identification.patch').read_bytes())
cmd=['patch','-p1','--batch','--fuzz=0','-i',str(patch)]
(root/'patch.args.json').write_text(json.dumps(cmd,indent=2)+'\n')
p=subprocess.run(cmd,cwd=root,capture_output=True);(root/'patch.stdout').write_bytes(p.stdout);(root/'patch.stderr').write_bytes(p.stderr);assert p.returncode==0,(p.stdout,p.stderr)
files=[('main.c',source)]+[(str(p.relative_to(root)),p.read_bytes()) for p in sorted((root/'include').rglob('*.h'))]
bundle,offsets=pack_files(files,['include']);incoming=b'CC-RUN\n'+bundle;(root/'native-input.bin').write_bytes(incoming)
compiler=root/'compiler32';shutil.copy2(base/'build/copy-c/compiler.stream.build/compiler32',compiler)
for rel in ['runtime/copy_c/compiler.fth','runtime/copy_c/preprocess_queries.h','runtime/copy_c/preprocess_macros.h','runtime/copy_c/input_files.h','runtime/copy_c/preprocess_include.h','runtime/copy_c/preprocess_condition.h','runtime/copy_c/preprocess_phase2.h','runtime/pforth/custom.c','runtime/pforth/clib.c','runtime/copy_c/integer64_fold.h','src/space.c','src/bitcopy.c','src/space_run.c','tests/space_segments.py','tests/space_trace_audit.py']:
 q=root/'sources'/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((base/rel).read_bytes())
(root/'run.py').write_bytes(Path(__file__).read_bytes())
r=subprocess.run([str(compiler)],input=incoming,capture_output=True,timeout=30)
(root/'compiler.stdout').write_bytes(r.stdout);(root/'compiler.stderr').write_bytes(r.stderr)
translation=b'#define main test_main\n'+source+b'\n#undef main\nvoid _start(void){unsigned value=test_main();int result;__asm__ volatile("int $0x80":"=a"(result):"0"(4),"b"(1),"c"(&value),"d"(4):"memory");__asm__ volatile("int $0x80"::"a"(1),"b"(result!=4):"memory");for(;;){}}\n'
(root/'gcc-source.c').write_bytes(translation)
cmd=['gcc','-m32','-std=gnu11','-O0','-ffreestanding','-nostdlib','-fno-pie','-no-pie','-fno-stack-protector','-I'+str(root/'include'),'-Wl,-e,_start',str(root/'gcc-source.c'),'-o',str(root/'gcc-reference')]
(root/'gcc.args.json').write_text(json.dumps(cmd,indent=2)+'\n')
g=subprocess.run(cmd,capture_output=True,timeout=30);(root/'gcc.stdout').write_bytes(g.stdout);(root/'gcc.stderr').write_bytes(g.stderr)
evidence={'linux':'6.12','original_headers':original_hashes,'patched_inputs':{n:hashlib.sha256(c).hexdigest() for n,c in files},'patch_sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),'compiler_sha256':hashlib.sha256(compiler.read_bytes()).hexdigest(),'compiler_status':r.returncode,'gcc_status':g.returncode,'scope':'native control compilation of explicitly patched kernel header; GCC uses its actual compiler branch; space compilation not proven'}
evidence['source_sha256']=hashlib.sha256(source).hexdigest()
evidence['native_input_sha256']=hashlib.sha256(incoming).hexdigest()
evidence['runtime_sources']={str(p.relative_to(root/'sources')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'sources').rglob('*') if p.is_file()}
(root/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
print('compiler status',r.returncode,'gcc status',g.returncode,flush=True)
if r.returncode: print(r.stdout[:200],flush=True)
if g.returncode: print(g.stderr[:200],flush=True)
assert r.returncode==g.returncode==0 and r.stderr==b''
ref=subprocess.run([str(root/'gcc-reference')],capture_output=True,timeout=30);(root/'gcc-result.out').write_bytes(ref.stdout);assert ref.returncode==0 and ref.stdout==(7).to_bytes(4,'little')
program=r.stdout
if not options.native_only:
 image_path=base/'build/copy-c/compiler.stream'
 image=image_path.read_bytes();image_manifest=json.loads(image_path.with_name(image_path.name+'.json').read_text())
 dictionary=image_manifest['compiler_dictionary']
 for key,relative in [('compiler_forth_sha256','runtime/copy_c/compiler.fth'),('compiler_custom_sha256','runtime/pforth/custom.c'),('compiler_preprocess_queries_sha256','runtime/copy_c/preprocess_queries.h'),('compiler_preprocess_macros_sha256','runtime/copy_c/preprocess_macros.h'),('compiler_preprocess_condition_sha256','runtime/copy_c/preprocess_condition.h'),('compiler_preprocess_phase2_sha256','runtime/copy_c/preprocess_phase2.h'),('compiler_input_files_sha256','runtime/copy_c/input_files.h'),('compiler_preprocess_include_sha256','runtime/copy_c/preprocess_include.h'),('compiler_integer64_fold_sha256','runtime/copy_c/integer64_fold.h')]:
  assert dictionary[key]==hashlib.sha256((root/'sources'/relative).read_bytes()).hexdigest(), 'rebuild stale guest image: '+key
 (root/'compiler.stream').write_bytes(image);(root/'compiler.json').write_text(json.dumps(image_manifest,indent=2)+'\n')
 (root/'in.bin').write_bytes(image+incoming)
 (root/'reference.in').write_bytes(program)
 emulator=root/'space-64m';shutil.copy2(base/'build/bin/space-64m',emulator)
 execution=execute_segments(emulator,root,root/'in.bin',space_bytes=image_manifest['space_bytes'],layer_bytes=image_manifest['layer_bits']//8,ticks=100000,timeout=3600,compression='zstd')
 raw=(root/'space.bin').read_bytes()
 def word(at):return sum(((raw[(at+i)//8]>>(7-(at+i)%8))&1)<<i for i in range(32))
 assert word(132128)==10 and word(132160)==0
 program=(root/'program.in').read_bytes();assert program==r.stdout
 evidence.update(execution);evidence['guest_exit']=word(132160)
 evidence['image_sha256']=hashlib.sha256(image).hexdigest()
 evidence['input_sha256']=hashlib.sha256((root/'in.bin').read_bytes()).hexdigest()
 evidence['scope']='compilation of explicitly patched Linux header inside Space; native control packet equality, GCC actual compiler branch and direct copies'
 (root/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
target=root/'target';target.mkdir();(target/'in.bin').write_bytes(program)
cmd=[str(base/'build/bin/space'),'--ticks','20000','--trace',str(target/'trace.txt'),'--dump-space',str(target/'space.bin')]
(target/'args.json').write_text(json.dumps(cmd,indent=2)+'\n')
t=subprocess.run(cmd,input=program,capture_output=True,timeout=60);(target/'result.out').write_bytes(t.stdout);(target/'stderr.txt').write_bytes(t.stderr)
assert t.returncode==0 and t.stdout==ref.stdout and t.stderr==b''
assert (target/'space.bin').read_bytes()[:2272]==bytes(2272) and (target/'trace.txt').read_bytes().splitlines()[-1].endswith(b' idle')
evidence['direct_copy_out']=t.stdout.hex();evidence['gcc_out']=ref.stdout.hex()
evidence['packet_sha256']=hashlib.sha256(program).hexdigest()
(root/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
print('OK Linux __KERNEL__ compiler_types.h:', 'native control' if options.native_only else 'compiler inside Space', '; GCC and direct copies OUT=7',flush=True)
