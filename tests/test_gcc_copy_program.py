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

def finish_guest(root,evidence,*,resume=False,max_parts=512,timeout=900,
                 emulator=None,channels_only=False,execution_name="linker",fork_from=None,
                 segment_ticks=None):
    assert evidence.get("guest_generation_pending"), "no pending guest generation"
    for name,digest in evidence["source_sha256"].items():
        assert hashlib.sha256((root/"sources"/name).read_bytes()).hexdigest()==digest, "changed frozen source"
    selected=root/str(evidence["guest_case"])
    incoming=(selected/"input.s").read_bytes()
    assert hashlib.sha256(incoming).hexdigest()==evidence["guest_assembly_sha256"], "changed assembly"
    expected=(selected/"image.bin").read_bytes()
    case=evidence["direct_cases"][evidence["guest_case"]]
    assert hashlib.sha256(expected).hexdigest()==case["image_sha256"], "changed expected image"
    assert (root/"in.bin").read_bytes()==(root/"linker.stream").read_bytes()+incoming, "changed guest input"
    manifest=json.loads((root/"linker.stream.json").read_text())
    profiles={2097152:"space",67108864:"space-64m",268435456:"space-256m"}
    guest_emulator=Path(emulator).resolve() if emulator else ROOT/"build/bin"/profiles[manifest["space_bytes"]]
    execution_folder=root/execution_name
    execution=execute_segments(guest_emulator,execution_folder,root/"in.bin",
        space_bytes=manifest["space_bytes"],layer_bytes=manifest["layer_bits"]//8,
        ticks=segment_ticks or evidence.get("segment_ticks",100000),timeout=timeout,
        compression="zstd",resume=resume,max_parts=max_parts,
        channels_only=channels_only,fork_from=fork_from)
    assert (execution_folder/"program.in").read_bytes()==expected
    raw=(execution_folder/"space.bin").read_bytes()
    def word(at):return sum(((raw[(at+i)//8]>>(7-(at+i)%8))&1)<<i for i in range(32))
    assert word(132128)==10 and word(132160)==0
    folder=root/"guest-result";folder.mkdir();(folder/"image.bin").write_bytes(expected)
    emulator=ROOT/"build/bin"/("space" if evidence["result_space_bytes"]==2097152 else "space-256m")
    command=[str(emulator),"--core",str(folder/"image.bin"),"--trace",str(folder/"trace.txt")]
    (folder/"command.json").write_text(json.dumps(command)+"\n")
    checked=subprocess.run(command,capture_output=True,check=True,timeout=30)
    value=case["result"]
    expected_output=b"" if value is None else struct.pack("<I",value)
    (folder/"out.bin").write_bytes(checked.stdout);assert checked.stdout==expected_output
    evidence.pop("guest_generation_pending")
    evidence.update({"guest_generation":execution,"guest_exit":word(132160),"guest_direct_result":value})
    (root/"evidence.json").write_text(json.dumps(evidence,indent=2)+"\n")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts",type=Path,required=True)
    parser.add_argument("--native-only",action="store_true")
    parser.add_argument("--sanitize",action="store_true",help="prepare the native linker with ASan/UBSan")
    parser.add_argument("--compiler")
    parser.add_argument("--newlib",type=Path)
    parser.add_argument("--result-space-bytes",type=int,choices=[2097152,268435456],default=2097152)
    parser.add_argument("--guest-case",type=int,default=0)
    parser.add_argument("--assembly",type=Path,help="also execute existing GCC output and use it for guest generation")
    parser.add_argument("--expected-result",type=lambda s:int(s,0),default=8)
    parser.add_argument("--direct-timeout",type=float,default=300,help="include large snapshot I/O in direct execution limit")
    parser.add_argument("--resume",action="store_true",help="continue pending guest generation from frozen artifacts")
    parser.add_argument("--max-parts",type=int,default=512)
    parser.add_argument("--guest-timeout",type=float,default=900)
    parser.add_argument("--segment-ticks",type=int,help="ticks per segment; default 100000 or frozen value on resume")
    parser.add_argument("--objects",action="store_true",help="test fixture accepts NUL-separated assembly units")
    parser.add_argument("--emulator",type=Path)
    parser.add_argument("--trace-channels",action="store_true")
    parser.add_argument("--execution-name",default="linker")
    parser.add_argument("--checkpoint-from",type=Path)
    args=parser.parse_args();root=args.artifacts.resolve()
    if args.max_parts<1:parser.error("--max-parts must be positive")
    if args.segment_ticks is not None and args.segment_ticks<1:parser.error("--segment-ticks must be positive")
    if args.resume and args.checkpoint_from:parser.error("choose resume or checkpoint-from")
    if args.execution_name in ("", ".", "..") or Path(args.execution_name).name!=args.execution_name:parser.error("execution-name must be a folder name")
    guest_options=dict(emulator=args.emulator,channels_only=args.trace_channels,
        execution_name=args.execution_name,fork_from=args.checkpoint_from)
    if args.resume or args.checkpoint_from:
        if args.native_only or args.assembly:parser.error("resume uses the frozen guest case")
        evidence=json.loads((root/"evidence.json").read_text())
        finish_guest(root,evidence,resume=args.resume,max_parts=args.max_parts,
            timeout=args.guest_timeout,segment_ticks=args.segment_ticks,**guest_options)
        print("OK resumed guest generation")
        return
    root.mkdir(parents=True,exist_ok=False)
    paths=[ROOT/"tests/fixtures/gcc/copy_link.c"]+[ROOT/"runtime/gcc"/name for name in ("copy_link.c","copy_link.h","copy_emit.c","copy_emit.h")]
    hashes={}
    for source in paths:
        destination=root/"sources"/source.relative_to(ROOT)
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(source.read_bytes())
        hashes[str(source.relative_to(ROOT))]=hashlib.sha256(destination.read_bytes()).hexdigest()
    sources=[root/"sources"/source.relative_to(ROOT) for source in paths if source.suffix==".c"]
    bits=(args.result_space_bytes*8).bit_length()-1
    flags=["-DCS_COPY_PROGRAM","-DCS_COPY_RESULT_ADDRESS_BITS="+str(bits),"-I"+str(root/"sources/runtime/gcc")]
    if args.objects:flags.append("-DCS_COPY_OBJECTS")
    command=["gcc","-O2","-Wall","-Wextra","-Werror"]+flags+[str(s) for s in sources]+["-o",str(root/"native")]
    if args.sanitize:
        command[1:1]=["-g","-fsanitize=address,undefined","-fno-omit-frame-pointer","-fno-pie","-no-pie"]
    (root/"native-command.json").write_text(json.dumps(command)+"\n")
    result=subprocess.run(command,capture_output=True);assert result.returncode==0,result.stderr
    cases=[
        (b'value:\ncopy.jsra helper\ncopy.inc $r0,1\ncopy.ret\nhelper:\ncopy.add $r0,$r1\ncopy.ret\n',8),
        (b'helper:\ncopy.add $r0,$r1\ncopy.ret\nvalue:\ncopy.jsra helper\ncopy.inc $r0,1\ncopy.ret\n',8),
        (b'value:\ncopy.jsra helper\ncopy.jsra helper\ncopy.ret\nhelper:\ncopy.inc $r0,1\ncopy.ret\n',5),
        (b'value:\ncopy.jsra helper\ncopy.ret\nhelper:\ncopy.jsra inner\ncopy.inc $r0,1\ncopy.ret\ninner:\ncopy.add $r0,$r1\ncopy.ret\n',8),
        (b'value:\ncopy.ldi.l $r2,0\ncopy.cmp $r0,$r2\ncopy.branch.eq .Lbase\ncopy.dec $r0,1\ncopy.jsra value\ncopy.inc $r0,2\n.Lbase:\ncopy.ret\n',6),
        (b'value:\ncopy.ldi.l $r6,12345\ncopy.jsra helper\ncopy.mov $r0,$r6\ncopy.ret\nhelper:\ncopy.push $sp,$r6\ncopy.ldi.l $r6,99\ncopy.mov $r12,$fp\ncopy.dec $r12,4\ncopy.pop $r12,$r6\ncopy.ret\n',12345),
        (b'value:\ncopy.jsra helper\ncopy.ret\nhelper:\ncopy.mov $r0,$sp\ncopy.ret\n',8144),
        (b'value:\ncopy.jsra helper\ncopy.mov $r0,$sp\ncopy.ret\nhelper:\ncopy.dec $sp,16\ncopy.ret\n',8156),
        (b'value:\ncopy.dec $sp,4\ncopy.ldi.l $r2,19\ncopy.st.l ($sp),$r2\ncopy.jsra helper\ncopy.ret\nhelper:\ncopy.ldo.l $r0,12($fp)\ncopy.ret\n',19),
        (b'value:\ncopy.ldi.l $r2,helper\ncopy.jsr $r2\ncopy.inc $r0,1\ncopy.ret\nhelper:\ncopy.add $r0,$r1\ncopy.ret\n',8),
        (b'value:\ncopy.ldi.l $r2,123\ncopy.sto.l -4($sp),$r2\ncopy.jsra helper\ncopy.ret\nhelper:\ncopy.ldo.l $r0,8($fp)\ncopy.ret\n',123),
        (b'value:\ncopy.ldi.l $r2,456\ncopy.sto.l -4($sp),$r2\ncopy.ldi.l $r3,helper\ncopy.jsr $r3\ncopy.ret\nhelper:\ncopy.ldo.l $r0,8($fp)\ncopy.ret\n',456),
        (b'value:\ncopy.ldi.l $r2,helper\ncopy.sta.l 16,$r2\ncopy.lda.l $r3,16\ncopy.jsr $r3\ncopy.ret\nhelper:\ncopy.add $r0,$r1\ncopy.ret\n',7),
        (b'value:\ncopy.ldi.l $r2,helper\ncopy.ldi.l $r3,helper\ncopy.cmp $r2,$r3\ncopy.branch.ne .Lbad\ncopy.jsr $r2\ncopy.ret\n.Lbad:\ncopy.ldi.l $r0,99\ncopy.ret\nhelper:\ncopy.inc $r0,1\ncopy.ret\n',4),
        (b'value:\ncopy.ldi.l $r2,.Lnext\ncopy.jmp $r2\n.Lskip:\ncopy.ldi.l $r0,99\ncopy.ret\n.Lnext:\ncopy.add $r0,$r1\ncopy.ret\n',7),
        (b'value:\ncopy.ldi.l $r2,helper\ncopy.jsr $r2\ncopy.ret\nhelper:\ncopy.ldi.l $r3,inner\ncopy.jsr $r3\ncopy.inc $r0,1\ncopy.ret\ninner:\ncopy.add $r0,$r1\ncopy.ret\n',8),
        (b'value:\ncopy.ldi.l $r2,0\ncopy.cmp $r0,$r2\ncopy.branch.eq .Lbase\ncopy.dec $r0,1\ncopy.ldi.l $r3,value\ncopy.jsr $r3\ncopy.inc $r0,2\n.Lbase:\ncopy.ret\n',6),
        (b'.data\n.p2align 2\nglobal:\n.long 5\n.text\nvalue:\ncopy.lda.l $r0,global\ncopy.inc $r0,2\ncopy.sta.l global,$r0\ncopy.lda.l $r0,global\ncopy.ret\n',7),
        (b'.bss\n.p2align 2\nzero:\n.zero 4\n.text\nvalue:\ncopy.lda.l $r0,zero\ncopy.ret\n',0),
        (b'.data\npointer:\n.long array+4\narray:\n.long 2,3,4\n.text\nvalue:\ncopy.lda.l $r2,pointer\ncopy.ld.l $r0,($r2)\ncopy.ret\n',3),
        (b'.data\ncallback:\n.long helper\n.text\nvalue:\ncopy.lda.l $r2,callback\ncopy.jsr $r2\ncopy.ret\nhelper:\ncopy.add $r0,$r1\ncopy.ret\n',7),
        (b'.section .rodata.str1.1,"aMS",@progbits,1\nmessage:\n.string "a#b\\000c"\n.text\nvalue:\ncopy.lda.b $r0,message+1\ncopy.ret\n',35),
        (b'.rodata\nbytes:\n.ascii "\\101\\x42\\n\\\\\\\""\n.text\nvalue:\ncopy.lda.l $r0,bytes\ncopy.ret\n',0x5c0a4241),
        (b'.data\n.byte 1\n.p2align 4\naligned:\n.long 9\n.text\nvalue:\ncopy.ldi.l $r0,aligned\ncopy.ret\n',272),
        (b'.local shared\n.comm shared,12,16\n.text\nvalue:\ncopy.lda.l $r0,shared+8\ncopy.ret\n',0),
        (b'.data\nwide:\n.quad 0x123456789abcdef0\n.text\nvalue:\ncopy.lda.l $r0,wide+4\ncopy.ret\n',0x12345678),
        (b'.data\nwide:\n.quad -9223372036854775808\n.text\nvalue:\ncopy.lda.l $r0,wide+4\ncopy.ret\n',0x80000000),
        (b'.data\nfirst:\n.byte 1,-1\n.short 0x2345\n.text\nvalue:\ncopy.lda.l $r0,first\ncopy.ret\n',0x2345ff01),
        (b'.section .kernel.text,"ax",@progbits\nvalue:\ncopy.add $r0,$r1\ncopy.ret\n',7),
        (b'.section .kernel.data,"aw",@progbits\nobject:\n.long 11\n.text\nvalue:\ncopy.lda.l $r0,object\ncopy.ret\n',11),
        (b'.section .kernel.bss,"aw",@nobits\nobject:\n.zero 4\n.text\nvalue:\ncopy.lda.l $r0,object\ncopy.ret\n',0),
        (b'.data\nfirst:\n.long 1\n.pushsection .rodata.extra,"a",@progbits\n.ascii "abcde"\n.popsection\nsecond:\n.long 2\n.text\nvalue:\ncopy.ldi.l $r0,second\ncopy.ldi.l $r1,first\ncopy.sub $r0,$r1\ncopy.ret\n',4),
        (b'.section .alpha,"aw"\nfirst:\n.long 1\n.section .beta,"aw"\n.byte 9\n.previous\nsecond:\n.long 2\n.text\nvalue:\ncopy.ldi.l $r0,second\ncopy.ldi.l $r1,first\ncopy.sub $r0,$r1\ncopy.ret\n',4),
        (b'.section .object,"aw"\nfirst:\n.long 1\n.text\nvalue:\ncopy.lda.l $r0,second\ncopy.ret\n.section .object\nsecond:\n.long 2\n',2),
        (b'.section .alpha,"aw"\n.byte 1\n.pushsection .beta,"aw"\n.p2align 4\nwide:\n.long 9\n.popsection\n.byte 2\n.text\nvalue:\ncopy.ldi.l $r0,wide\ncopy.ret\n',272),
        (b'.data\nobject:\n.long 9\n.set view,object\n.set forward,view\n.text\nvalue:\ncopy.lda.l $r0,forward\ncopy.ret\n',9),
        (b'.set wrapper,helper\n.text\nvalue:\ncopy.jsra wrapper\ncopy.ret\nhelper:\ncopy.add $r0,$r1\ncopy.ret\n',7),
        (b'.equ constant,11\n.text\nvalue:\ncopy.ldi.l $r0,constant\ncopy.ret\n',11),
        (b'.weak optional\nvalue:\ncopy.ldi.l $r0,optional\ncopy.ret\n',0),
        (b'.weak optional\nvalue:\ncopy.ldi.l $r2,optional\ncopy.ldi.l $r3,0\ncopy.cmp $r2,$r3\ncopy.branch.eq .Lnone\ncopy.jsra optional\ncopy.ret\n.Lnone:\ncopy.add $r0,$r1\ncopy.ret\n',7),
        (b'.weak optional\nvalue:\ncopy.jsra optional\ncopy.ret\noptional:\ncopy.add $r0,$r1\ncopy.ret\n',7),
        (b'.weak optional\n.set alias,optional\nvalue:\ncopy.ldi.l $r0,alias\ncopy.ret\n',0),
        (b'.weak optional\n.set alias,optional\nvalue:\ncopy.jsra alias\ncopy.ret\n',None),
        (b'.weak optional\nvalue:\ncopy.jsra optional\ncopy.ret\n',None),
        (b'.weak optional\n.data\ncallback:\n.long optional\n.text\nvalue:\ncopy.lda.l $r0,callback\ncopy.ret\n',0),
        (b'.weak one,two\nvalue:\ncopy.ldi.l $r0,one\ncopy.ldi.l $r1,two\ncopy.or $r0,$r1\ncopy.ret\n',0)]
    # 253 user constants plus three constants used by the return frame fill
    # the pool exactly. Check accumulation across the whole pool's extent.
    large=b'value:\n'+b''.join((f'copy.ldi.l $r2,{65536+i}\n'+('copy.add $r0,$r2\n' if i%16==0 else '')).encode() for i in range(253))+b'copy.ret\n'
    cases.append((large,3+sum(65536+i for i in range(253) if i%16==0)))
    cases.append((b'value:\n'+b'copy.ldi.l $r0,123456\n'*300+b'copy.ret\n',123456))
    cases.append((b'value:\ncopy.sto.l 12($fp),$r0\ncopy.sto.l 32($fp),$r1\n'
                  b'copy.ldo.l $r0,12($fp)\ncopy.ldo.l $r1,32($fp)\ncopy.add $r0,$r1\ncopy.ret\n',7))
    cases.append((b'value:\ncopy.sto.l 12($fp),$r0\ncopy.sto.l 32($fp),$r1\n'
                  b'copy.dec $sp,24\ncopy.jsra helper\ncopy.ldo.l $r0,12($fp)\n'
                  b'copy.ldo.l $r1,32($fp)\ncopy.add $r0,$r1\ncopy.ret\n'
                  b'helper:\ncopy.ldi.l $r0,99\ncopy.sto.l 12($fp),$r0\n'
                  b'copy.sto.l 32($fp),$r0\ncopy.ret\n',7))
    if args.assembly:
        if not 0<=args.expected_result<=0xffffffff:raise ValueError("expected result must fit uint32")
        cases.append((args.assembly.read_bytes(),args.expected_result))
        args.guest_case=len(cases)-1
    if not 0<=args.guest_case<len(cases):raise ValueError("invalid guest case")
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
        checked=subprocess.run(command,capture_output=True,check=True,timeout=args.direct_timeout)
        expected_output=b"" if value is None else struct.pack("<I",value)
        (folder/"out.bin").write_bytes(checked.stdout);assert checked.stdout==expected_output,(index,checked.stdout)
        raw=(folder/"space.bin").read_bytes()
        def word(at):return sum(((raw[(at+i)//8]>>(7-(at+i)%8))&1)<<i for i in range(32))
        if value is not None:
            assert word(32768)==8192 and word(32800)==8192,(index,word(32768),word(32800))
        if args.result_space_bytes>2097152:
            with gzip.open(folder/"space.bin.gz","wb",compresslevel=1) as stream:stream.write(raw)
            (folder/"space.bin").unlink()
        results.append({"result":value,"final_fp":word(32768),"final_sp":word(32800),"image_sha256":hashlib.sha256(result.stdout).hexdigest()})
        if index==args.guest_case:incoming=assembly
    invalid=[b'value:\ncopy.jsra missing\ncopy.ret\n',b'other:\ncopy.ret\n',
             b'value:\ncopy.jsra helper\ncopy.ret\nhelper:\ncopy.ret\nhelper:\ncopy.ret\n',
             b'value:\ncopy.ldi.l $r2,missing\ncopy.ret\n',
             b'value:\ncopy.jsr $r99\ncopy.ret\n',
             b'value:\ncopy.jmp symbol\n.Lend:\ncopy.ret\n',
             b'.data\nx:\n.zero 4096\n.text\nvalue:\ncopy.ret\n',
             b'.data\nx:\n.long missing+4\n.text\nvalue:\ncopy.ret\n',
             b'.data\nx:\n.long 1\n.text\nvalue:\ncopy.jsra x\ncopy.ret\n',
             b'.bss\nx:\n.long 1\n.text\nvalue:\ncopy.ret\n',
             b'.data\nx:\n.p2align 33\n.text\nvalue:\ncopy.ret\n',
             b'.data\nx:\n.string "unterminated\n.text\nvalue:\ncopy.ret\n',
             b'.data\nx:\n.quad 18446744073709551616\n.text\nvalue:\ncopy.ret\n',
             b'.set a,b\n.set b,a\n.text\nvalue:\ncopy.ret\n',
             b'.set a,missing\n.text\nvalue:\ncopy.ret\n',
             b'.set a,target\n.data\na:\n.long 1\n.text\ntarget:\ncopy.ret\nvalue:\ncopy.ret\n',
             b'.popsection\nvalue:\ncopy.ret\n',
             b'.previous\nvalue:\ncopy.ret\n',
             b'value:\ncopy.ret\n.pushsection .data\n',
             b'.weak\nvalue:\ncopy.ret\n',
             b'.weak optional,\nvalue:\ncopy.ret\n']
    invalid.append(b'value:\n'+b''.join(f'copy.ldi.l $r0,{65536+i}\n'.encode() for i in range(254))+b'copy.ret\n')
    for assembly in invalid:
        result=subprocess.run([str(root/"native")],input=assembly,capture_output=True)
        assert result.returncode==2 and not result.stdout
    evidence={"scope":"call frames, function addresses and initial data sections; objects mode supports initial separate linking",
        "objects_mode":args.objects,"source_sha256":hashes,
        "result_space_bytes":args.result_space_bytes,"direct_cases":results,"rejected_cases":len(invalid)}
    evidence.update({"guest_case":args.guest_case,"guest_assembly_sha256":hashlib.sha256(incoming).hexdigest()})
    evidence["segment_ticks"]=args.segment_ticks or 100000
    if not args.native_only:
        if not args.newlib:raise ValueError("--newlib required for guest generation")
        prefix=args.newlib.resolve()/"riscv64-unknown-elf"
        build(sources,root/"linker.stream",compiler=args.compiler,stream=True,optimization="-O2",
            memory_bytes=1024*1024,space_bytes=64*1024*1024,
            extra_cflags=flags+["-isystem",str(prefix/"include"),"-DCS_RUNTIME_EXTERNAL_MEMORY"],
            extra_libraries=["-Wl,--start-group",str(prefix/"lib/libc.a"),"-lgcc","-Wl,--end-group"])
        (root/"in.bin").write_bytes((root/"linker.stream").read_bytes()+incoming)
        evidence["guest_generation_pending"]=True
        (root/"evidence.json").write_text(json.dumps(evidence,indent=2)+"\n")
        finish_guest(root,evidence,max_parts=args.max_parts,timeout=args.guest_timeout,**guest_options)
    (root/"evidence.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print("OK direct call frames:",len(results),"programs")

if __name__=="__main__":main()
