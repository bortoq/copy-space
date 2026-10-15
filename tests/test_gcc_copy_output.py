"""Check in-process guest copy lowering; mock cc1 is not a compiler proof."""
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

def job(assembly,options,objects=()):
    inputs=[(b'in.s',assembly)]+[(name.encode(),data) for name,data in objects]
    files=b"\0CCFILES1"+struct.pack("<III",len(inputs),0,0)
    files+=b''.join(struct.pack('<II',len(name),len(data))+name+data for name,data in inputs)
    argv=[b"cc1"]+[x.encode() for x in options]+[b"-S",b"in.s"]
    return b"GCCJOB1\0"+struct.pack("<II",len(argv),len(files))+b"".join(struct.pack("<I",len(a))+a for a in argv)+files

def decode(packet):
    assert packet[:8]==b"GCCOUT1\0" and len(packet)>=24
    code,out,err,size=struct.unpack_from("<IIII",packet,8)
    assert len(packet)==24+out+err+size
    return code,packet[24:24+out],packet[24+out:24+out+err],packet[24+out+err:]

def direct(image,folder,expected):
    folder.mkdir();(folder/"image.bin").write_bytes(image)
    command=[str(ROOT/"build/bin/space"),"--core",str(folder/"image.bin"),"--trace",str(folder/"trace.txt")]
    (folder/"command.json").write_text(json.dumps(command)+"\n")
    result=subprocess.run(command,capture_output=True,check=True,timeout=10)
    (folder/"out.bin").write_bytes(result.stdout)
    assert result.stdout==struct.pack("<I",expected)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifacts",type=Path,required=True)
    p.add_argument("--native-only",action="store_true")
    p.add_argument("--compiler")
    p.add_argument("--newlib",type=Path)
    args=p.parse_args();root=args.artifacts.resolve();root.mkdir(parents=True,exist_ok=False)
    names=["tests/fixtures/gcc/copy_output.c"]+["runtime/gcc/"+n for n in
        ("main.c","job.c","job.h","files.c","files.h","response.c","response.h",
         "copy_link.c","copy_link.h","copy_emit.c","copy_emit.h","syscalls.c","start.S","link.ld")]
    names+= ["runtime/copy_c/input_files.h","runtime/rv32i/copy_space.h"]
    hashes={}
    for name in names:
        path=root/"sources"/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes((ROOT/name).read_bytes());hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    sources=[root/"sources"/name for name in names if name.endswith(".c") and not name.endswith("syscalls.c")]
    flags=["-DCS_GCC_FRAMED_OUTPUT","-DCS_GCC_COPY_OUTPUT","-Wl,--wrap=main",
        "-I"+str(root/"sources/runtime/gcc"),"-I"+str(root/"sources/runtime/rv32i")]
    command=["gcc","-O2","-Wall","-Wextra","-Werror"]+flags+[str(s) for s in sources]+["-o",str(root/"native")]
    (root/"native-command.json").write_text(json.dumps(command)+"\n")
    result=subprocess.run(command,capture_output=True);assert result.returncode==0,result.stderr
    options=["--space-copy=result.s","--space-entry=value","--space-arg=3","--space-arg=0x4"]
    assembly=b".text\nvalue:\ncopy.add $r0,$r1\ncopy.ret\n"
    incoming=job(assembly,options);(root/"job.bin").write_bytes(incoming)
    good=subprocess.run([str(root/"native")],input=incoming,capture_output=True)
    code,out,err,image=decode(good.stdout)
    assert good.returncode==code==0 and not out and not err and len(image)==65536
    direct(image,root/"native-result",7)
    program_options=["--space-program=result.s"]+options[1:]
    program_asm=b'value:\ncopy.jsra helper\ncopy.inc $r0,1\ncopy.ret\nhelper:\ncopy.add $r0,$r1\ncopy.ret\n'
    program=subprocess.run([str(root/"native")],input=job(program_asm,program_options),capture_output=True)
    status,stdout,stderr,file=decode(program.stdout)
    assert program.returncode==status==0 and not stdout and not stderr and len(file)==262144
    direct(file,root/"program-result",8)
    for memory in (8192,16384,32768,65536,131072):
        packet=job(b'value:\ncopy.mov $r0,$sp\ncopy.ret\n',program_options+["--space-memory="+str(memory)])
        (root/f"memory-{memory}.job").write_bytes(packet)
        run=subprocess.run([str(root/"native")],input=packet,capture_output=True)
        status,stdout,stderr,file=decode(run.stdout)
        assert run.returncode==status==0 and not stdout and not stderr
        direct(file,root/f"memory-{memory}",memory-36)
    explicit=subprocess.run([str(root/"native")],input=job(program_asm,program_options+["--space-memory=8192"]),capture_output=True)
    assert explicit.stdout==program.stdout
    scaled_flags=["-DCS_GCC_COPY_PROGRAM_BYTES=2097152", "-DCS_COPY_LABEL_CAPACITY=128",
                  "-DCS_COPY_JUMP_CAPACITY=512", "-DCS_COPY_CALL_CAPACITY=64"]
    scaled_command=command[:-2]+scaled_flags+["-o",str(root/"scaled")]
    (root/"scaled-command.json").write_text(json.dumps(scaled_command)+"\n")
    subprocess.run(scaled_command,capture_output=True,check=True)
    many_calls=b'value:\n'+b'copy.jsra helper\n'*40+b'copy.ret\nhelper:\ncopy.inc $r0,1\ncopy.ret\n'
    for name,body,private,expected in (
        ("scaled-calls",many_calls,program_options,43),
        ("scaled-memory",b'value:\ncopy.mov $r0,$sp\ncopy.ret\n',
         program_options+["--space-memory=1048576"],1048576-36)):
        packet=job(body,private);(root/(name+".job")).write_bytes(packet)
        result=subprocess.run([str(root/"scaled")],input=packet,capture_output=True)
        status,stdout,stderr,file=decode(result.stdout)
        assert result.returncode==status==0 and not stdout and not stderr and len(file)==2097152
        direct(file,root/name,expected)
    for memory in (2097152,4194304):
        result=subprocess.run([str(root/"scaled")],input=job(program_asm,
            program_options+["--space-memory="+str(memory)]),capture_output=True)
        assert result.returncode==125 and not result.stdout
    invalid_memory=["", "0", "4096", "8193", "262144", "4294967296", "-8192", "+8192", " 8192", "08", "8192junk"]
    for number in invalid_memory:
        result=subprocess.run([str(root/"native")],input=job(program_asm,program_options+["--space-memory="+number]),capture_output=True)
        assert result.returncode==125 and not result.stdout
    result=subprocess.run([str(root/"native")],input=job(assembly,options+["--space-memory=8192"]),capture_output=True)
    assert result.returncode==125 and not result.stdout
    for name,body,private,expected in (
        ("default",b"main:\ncopy.ldi.l $r0,9\ncopy.ret\n",["--space-copy=result.s"],9),
        ("six-args",b"value:\ncopy.mov $r0,$r5\ncopy.ret\n",
         options[:2]+["--space-arg="+str(i) for i in (3,4,5,6,7,8)],8)):
        result=subprocess.run([str(root/"native")],input=job(body,private),capture_output=True)
        status,stdout,stderr,file=decode(result.stdout)
        assert result.returncode==status==0 and not stdout and not stderr
        direct(file,root/name,expected)
    invalid=["", "-1","+1","4294967296","08"," 3","\t3","3junk"]
    for index,number in enumerate(invalid):
        packet=job(assembly,options[:2]+["--space-arg="+number])
        result=subprocess.run([str(root/"native")],input=packet,capture_output=True)
        assert result.returncode==125 and not result.stdout,(number,result)
        (root/f"invalid-{index}.bin").write_bytes(packet)
    for private in (["--space-copy="],["--space-copy=-"],
                    ["--space-copy=result.s","--space-entry="],
                    options[:2]+["--space-arg=1"]*7):
        result=subprocess.run([str(root/"native")],input=job(assembly,private),capture_output=True)
        assert result.returncode==125 and not result.stdout,result
    failed=subprocess.run([str(root/"native")],input=job(b"value:\ncopy.mul.x $r0,$r1\ncopy.ret\n",options),capture_output=True)
    status,stdout,stderr,file=decode(failed.stdout)
    assert failed.returncode==status==126 and not stdout and not file and b"unsupported operation" in stderr
    evidence={"scope":"adapter with mock cc1, not actual compilation","sources_sha256":hashes,
        "native_direct_result":7,"rejected_arguments":len(invalid)+4,"rejected_lowering":status}
    evidence["native_program_result"]=8
    evidence["scaled_program"]={"image_bytes":2097152,"calls":40,"result":43,
        "memory_bytes":1048576,"memory_result":1048576-36}
    evidence.update({"memory_sizes_checked":[8192,16384,32768,65536,131072],
        "rejected_memory_arguments":len(invalid_memory)+1,"default_program_image_unchanged":True})
    if not args.native_only:
        if not args.newlib: raise ValueError("guest check requires --newlib")
        prefix=args.newlib.resolve()/"riscv64-unknown-elf"
        guest_sources=sources+[root/"sources/runtime/gcc/syscalls.c"]
        manifest=build(guest_sources,root/"program.stream",compiler=args.compiler,stream=True,
            optimization="-O2",memory_bytes=1024*1024,space_bytes=64*1024*1024,
            extra_cflags=flags+["-DCS_RUNTIME_EXTERNAL_MEMORY","-DCS_GCC_MEMORY_BYTES=1048576",
                "-isystem",str(prefix/"include"),"-ffunction-sections","-fdata-sections","-Wl,--gc-sections"],
            extra_libraries=["-Wl,--start-group",str(prefix/"lib/libc.a"),"-lgcc","-Wl,--end-group"],
            startup=root/"sources/runtime/gcc/start.S",linker_script=root/"sources/runtime/gcc/link.ld")
        (root/"in.bin").write_bytes((root/"program.stream").read_bytes()+incoming)
        execution=execute_segments(ROOT/"build/bin/space-64m",root/"space",root/"in.bin",
            space_bytes=manifest["space_bytes"],layer_bytes=manifest["layer_bits"]//8,
            ticks=100000,timeout=900,compression="zstd")
        packet=(root/"space/program.in").read_bytes();assert packet==good.stdout
        raw=(root/"space/space.bin").read_bytes()
        def word(at):return sum(((raw[(at+i)//8]>>(7-(at+i)%8))&1)<<i for i in range(32))
        assert word(132128)==10 and word(132160)==0
        direct(decode(packet)[3],root/"guest-result",7)
        evidence.update({"guest_execution":execution,"guest_exit":word(132160),"guest_direct_result":7})
    (root/"evidence.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print("OK integrated copy output adapter; direct result 7")

if __name__=="__main__": main()
