"""Lower copy assembly inside Space, then execute its output without RV32I."""
import argparse
import hashlib
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
    parser.add_argument("--compiler",required=True)
    parser.add_argument("--newlib",type=Path,required=True)
    parser.add_argument("--assembly",type=Path,help="use an existing GCC-produced assembler file for guest lowering")
    parser.add_argument("--native-only",action="store_true",help="check direct images without building the guest assembler")
    args=parser.parse_args()
    root=args.artifacts.resolve();root.mkdir(parents=True,exist_ok=False)
    paths=[ROOT/"tests/fixtures/gcc/copy_link.c"]+[ROOT/"runtime/gcc"/name for name in
        ("copy_link.c","copy_link.h","copy_emit.c","copy_emit.h")]
    hashes={}
    for source in paths:
        destination=root/"sources"/source.relative_to(ROOT)
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(source.read_bytes())
        hashes[str(source.relative_to(ROOT))]=hashlib.sha256(destination.read_bytes()).hexdigest()
    sources=[root/"sources"/source.relative_to(ROOT) for source in paths if source.suffix==".c"]
    include="-I"+str(root/"sources/runtime/gcc")
    native=root/"native"
    command=["gcc","-O2","-Wall","-Wextra","-Werror",include]+[str(s) for s in sources]+["-o",str(native)]
    (root/"native-command.json").write_text(json.dumps(command)+"\n")
    subprocess.run(command,check=True,capture_output=True)
    # These are assembler fixtures, not a claim of actual GCC output yet.
    prefix=b'.file "test.c"\n.text\n.p2align 1\n.global value\n.type value,@function\nvalue:\n'
    suffix=b'copy.ret\n.size value,.-value\n.ident "assembler test fixture"\n'
    cases=[(b'copy.add $r0,$r1\ncopy.ldi.l $r2,5\ncopy.xor $r0,$r2\n',2),
           (b'copy.add $r0,$r1\ncopy.sub $r0,$r1\n',3),
           (b'copy.or $r0,$r1\ncopy.and $r0,$r1\n',4),
           (b'copy.ldi.l $r0,0xffffffff\ncopy.inc $r0,1\ncopy.dec $r0,--5\n',0xfffffffb),
           (b'copy.ldi.l $r2,010\ncopy.mov $r0,$r2\n',8)]
    cases.extend([(b'copy.jmpa .Ldone\n.Lskip:\ncopy.ldi.l $r0,99\ncopy.ret\n.Ldone:\ncopy.add $r0,$r1\n',7),
                  (b'copy.jmpa .Llast\n.Lfirst:\ncopy.add $r0,$r1\ncopy.ret\n.Llast:\ncopy.jmpa .Lfirst\n.Lunused:\n',7),
                  (b'copy.add $r0,$r1\n.Lalias:\ncopy.xor $r0,$r1\n',3)])
    cases.append((b'copy.ret\n.Lunreachable:\ncopy.ldi.l $r0,99\n',3))
    results=[]
    for index,(body,value) in enumerate(cases):
        folder=root/str(index);folder.mkdir()
        assembly=prefix+body+(suffix if index<8 else b'.size value,.-value\n')
        (folder/"input.s").write_bytes(assembly)
        result=subprocess.run([str(native)],input=assembly,capture_output=True,check=True)
        assert len(result.stdout)==32768
        (folder/"image.bin").write_bytes(result.stdout)
        command=[str(ROOT/"build/bin/space"),"--core",str(folder/"image.bin"),"--trace",str(folder/"trace.txt")]
        (folder/"command.json").write_text(json.dumps(command)+"\n")
        checked=subprocess.run(command,capture_output=True,check=True,timeout=10)
        (folder/"out.bin").write_bytes(checked.stdout)
        assert checked.stdout==struct.pack("<I",value),checked.stdout
        results.append({"image_sha256":hashlib.sha256(result.stdout).hexdigest(),"output_hex":checked.stdout.hex()})
        if index==0: incoming,expected=assembly,result.stdout
    bad_bodies=[b'copy.mul $r0,$r1\n',b'copy.mov $r99,$r0\n',b'copy.ldi.l $r0,4294967296\n',
                b'copy.ldi.l $r0,08\n',b'copy.jmpa elsewhere\n']
    invalid=[prefix+s+suffix for s in bad_bodies]+[b'.data\nvalue:\ncopy.ret\n',
        prefix+b'copy.add $r0,$r1\n',prefix+b'other:\ncopy.ret\n',
        prefix+b'copy.ret\ncopy.add $r0,$r1\n',prefix+b'copy.ret\x00\n']
    invalid.extend([prefix+b'copy.jmpa .Lmissing\n'+suffix,
                    prefix+b'.Ldup:\n.Ldup:\n'+suffix])
    for index,assembly in enumerate(invalid):
        (root/f"invalid-{index}.s").write_bytes(assembly)
        result=subprocess.run([str(native)],input=assembly,capture_output=True)
        assert result.returncode==2 and not result.stdout,(index,result.returncode)
    if args.native_only:
        (root/"evidence.json").write_text(json.dumps({"source_sha256":hashes,
            "native_direct_cases":results,"rejected_cases":len(invalid)},indent=2)+"\n")
        print(f"OK {len(results)} direct images and {len(invalid)} rejected inputs")
        return
    if args.assembly:
        incoming=args.assembly.read_bytes()
        (root/"gcc-input.s").write_bytes(incoming)
        result=subprocess.run([str(native)],input=incoming,capture_output=True,check=True)
        expected=result.stdout
        assert len(expected)==32768
    prefix=args.newlib.resolve()/"riscv64-unknown-elf"
    manifest=build(sources,root/"linker.stream",compiler=args.compiler,stream=True,optimization="-O2",
        extra_cflags=[include,"-isystem",str(prefix/"include"),"-DCS_RUNTIME_EXTERNAL_MEMORY"],
        extra_libraries=["-Wl,--start-group",str(prefix/"lib/libc.a"),"-lgcc","-Wl,--end-group"])
    (root/"in.bin").write_bytes((root/"linker.stream").read_bytes()+incoming)
    execution=execute_segments(ROOT/"build/bin/space",root/"linker",root/"in.bin",
        space_bytes=manifest["space_bytes"],layer_bytes=manifest["layer_bits"]//8,
        ticks=100000,timeout=300,compression="zstd")
    output=(root/"linker/program.in").read_bytes();assert output==expected
    raw=(root/"linker/space.bin").read_bytes()
    def word(at):return sum(((raw[(at+i)//8]>>(7-(at+i)%8))&1)<<i for i in range(32))
    assert word(132128)==10 and word(132160)==0
    direct=root/"guest-result";direct.mkdir();(direct/"image.bin").write_bytes(output)
    command=[str(ROOT/"build/bin/space"),"--core",str(direct/"image.bin"),"--trace",str(direct/"trace.txt")]
    (direct/"command.json").write_text(json.dumps(command)+"\n")
    checked=subprocess.run(command,capture_output=True,check=True,timeout=10)
    (direct/"out.bin").write_bytes(checked.stdout);assert checked.stdout==struct.pack("<I",2)
    (root/"evidence.json").write_text(json.dumps({"scope":"guest leaf assembler prototype; actual GCC integration still required",
        "source_sha256":hashes,"native_direct_cases":results,"rejected_cases":len(invalid),
        "guest_link_execution":execution,"guest_exit":word(132160),
        "guest_image_sha256":hashlib.sha256(output).hexdigest(),"direct_output_hex":checked.stdout.hex()},indent=2)+"\n")
    print("OK guest copy assembler generated direct image; mixed add/XOR returned 2 without RV32I")


if __name__=="__main__":main()
