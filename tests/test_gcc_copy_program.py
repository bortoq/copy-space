"""Prove direct call frames by executing generated copies, with optional guest generation."""
import argparse
import hashlib
import gzip
import json
import struct
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts/rv32i"))
from build import build
from space_segments import execute_segments

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts",type=Path,required=True)
    parser.add_argument("--native-only",action="store_true")
    parser.add_argument("--compiler")
    parser.add_argument("--newlib",type=Path)
    parser.add_argument("--result-space-bytes",type=int,choices=[2097152,268435456],default=2097152)
    args=parser.parse_args();root=args.artifacts.resolve();root.mkdir(parents=True,exist_ok=False)
    paths=[ROOT/"tests/fixtures/gcc/copy_link.c"]+[ROOT/"runtime/gcc"/name for name in ("copy_link.c","copy_link.h","copy_emit.c","copy_emit.h")]
    hashes={}
    for source in paths:
        destination=root/"sources"/source.relative_to(ROOT)
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(source.read_bytes())
        hashes[str(source.relative_to(ROOT))]=hashlib.sha256(destination.read_bytes()).hexdigest()
    sources=[root/"sources"/source.relative_to(ROOT) for source in paths if source.suffix==".c"]
    bits=(args.result_space_bytes*8).bit_length()-1
    flags=["-DCS_COPY_PROGRAM","-DCS_COPY_RESULT_ADDRESS_BITS="+str(bits),"-I"+str(root/"sources/runtime/gcc")]
    command=["gcc","-O2","-Wall","-Wextra","-Werror"]+flags+[str(s) for s in sources]+["-o",str(root/"native")]
    (root/"native-command.json").write_text(json.dumps(command)+"\n")
    result=subprocess.run(command,capture_output=True);assert result.returncode==0,result.stderr
    cases=[
        (b'value:\ncopy.jsra helper\ncopy.inc $r0,1\ncopy.ret\nhelper:\ncopy.add $r0,$r1\ncopy.ret\n',8),
        (b'helper:\ncopy.add $r0,$r1\ncopy.ret\nvalue:\ncopy.jsra helper\ncopy.inc $r0,1\ncopy.ret\n',8),
        (b'value:\ncopy.jsra helper\ncopy.jsra helper\ncopy.ret\nhelper:\ncopy.inc $r0,1\ncopy.ret\n',5),
        (b'value:\ncopy.jsra helper\ncopy.ret\nhelper:\ncopy.jsra inner\ncopy.inc $r0,1\ncopy.ret\ninner:\ncopy.add $r0,$r1\ncopy.ret\n',8),
        (b'value:\ncopy.ldi.l $r2,0\ncopy.cmp $r0,$r2\ncopy.branch.eq .Lbase\ncopy.dec $r0,1\ncopy.jsra value\ncopy.inc $r0,2\n.Lbase:\ncopy.ret\n',6),
        (b'value:\ncopy.ldi.l $r6,12345\ncopy.jsra helper\ncopy.mov $r0,$r6\ncopy.ret\nhelper:\ncopy.push $sp,$r6\ncopy.ldi.l $r6,99\ncopy.mov $r12,$fp\ncopy.dec $r12,4\ncopy.pop $r12,$r6\ncopy.ret\n',12345),
        (b'value:\ncopy.jsra helper\ncopy.ret\nhelper:\ncopy.mov $r0,$sp\ncopy.ret\n',8168),
        (b'value:\ncopy.jsra helper\ncopy.mov $r0,$sp\ncopy.ret\nhelper:\ncopy.dec $sp,16\ncopy.ret\n',8180),
        (b'value:\ncopy.dec $sp,4\ncopy.ldi.l $r2,19\ncopy.st.l ($sp),$r2\ncopy.jsra helper\ncopy.ret\nhelper:\ncopy.ldo.l $r0,12($fp)\ncopy.ret\n',19)]
    emulator=ROOT/"build/bin"/("space" if bits==24 else "space-256m")
    results=[]
    for index,(assembly,value) in enumerate(cases):
        folder=root/str(index);folder.mkdir();(folder/"input.s").write_bytes(assembly)
        result=subprocess.run([str(root/"native")],input=assembly,capture_output=True)
        assert result.returncode==0,(index,result.stderr)
        assert len(result.stdout)==262144
        (folder/"image.bin").write_bytes(result.stdout)
        command=[str(emulator),"--core",str(folder/"image.bin"),"--trace",str(folder/"trace.txt"),"--dump-space",str(folder/"space.bin")]
        (folder/"command.json").write_text(json.dumps(command)+"\n")
        checked=subprocess.run(command,capture_output=True,check=True,timeout=30)
        (folder/"out.bin").write_bytes(checked.stdout);assert checked.stdout==struct.pack("<I",value),(index,checked.stdout)
        raw=(folder/"space.bin").read_bytes()
        def word(at):return sum(((raw[(at+i)//8]>>(7-(at+i)%8))&1)<<i for i in range(32))
        assert word(32768)==8192 and word(32800)==8192,(index,word(32768),word(32800))
        if args.result_space_bytes>2097152:
            with gzip.open(folder/"space.bin.gz","wb",compresslevel=1) as stream:stream.write(raw)
            (folder/"space.bin").unlink()
        results.append({"result":value,"final_fp":word(32768),"final_sp":word(32800),"image_sha256":hashlib.sha256(result.stdout).hexdigest()})
        if index==0:incoming,expected=assembly,result.stdout
    invalid=[b'value:\ncopy.jsra missing\ncopy.ret\n',b'other:\ncopy.ret\n',
             b'value:\ncopy.jsra helper\ncopy.ret\nhelper:\ncopy.ret\nhelper:\ncopy.ret\n']
    for assembly in invalid:
        result=subprocess.run([str(root/"native")],input=assembly,capture_output=True)
        assert result.returncode==2 and not result.stdout
    evidence={"scope":"call frames, no data sections or indirect calls","source_sha256":hashes,
        "result_space_bytes":args.result_space_bytes,"direct_cases":results,"rejected_cases":len(invalid)}
    if not args.native_only:
        if not args.newlib:raise ValueError("--newlib required for guest generation")
        prefix=args.newlib.resolve()/"riscv64-unknown-elf"
        manifest=build(sources,root/"linker.stream",compiler=args.compiler,stream=True,optimization="-O2",
            memory_bytes=1024*1024,space_bytes=64*1024*1024,
            extra_cflags=flags+["-isystem",str(prefix/"include"),"-DCS_RUNTIME_EXTERNAL_MEMORY"],
            extra_libraries=["-Wl,--start-group",str(prefix/"lib/libc.a"),"-lgcc","-Wl,--end-group"])
        (root/"in.bin").write_bytes((root/"linker.stream").read_bytes()+incoming)
        execution=execute_segments(ROOT/"build/bin/space-64m",root/"linker",root/"in.bin",
            space_bytes=manifest["space_bytes"],layer_bytes=manifest["layer_bits"]//8,ticks=100000,timeout=900,compression="zstd")
        assert (root/"linker/program.in").read_bytes()==expected
        raw=(root/"linker/space.bin").read_bytes()
        def word(at):return sum(((raw[(at+i)//8]>>(7-(at+i)%8))&1)<<i for i in range(32))
        assert word(132128)==10 and word(132160)==0
        folder=root/"guest-result";folder.mkdir();(folder/"image.bin").write_bytes(expected)
        command=[str(emulator),"--core",str(folder/"image.bin"),"--trace",str(folder/"trace.txt")]
        (folder/"command.json").write_text(json.dumps(command)+"\n")
        checked=subprocess.run(command,capture_output=True,check=True,timeout=30)
        (folder/"out.bin").write_bytes(checked.stdout);assert checked.stdout==struct.pack("<I",8)
        evidence.update({"guest_generation":execution,"guest_exit":word(132160),"guest_direct_result":8})
    (root/"evidence.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print("OK direct call frames:",len(results),"programs")

if __name__=="__main__":main()
