"""Execute actual cc1 in primitive Space; host GCC is an output oracle only."""
import argparse
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts/rv32i"))
from space_segments import execute_segments
from build import build


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image",type=Path,required=True,help="directory prepared by prepare_image.py")
    parser.add_argument("--artifacts",type=Path,required=True)
    parser.add_argument("--emulator",type=Path)
    parser.add_argument("--mode",choices=["preprocess","compile","copy-compile","integrated-copy","integrated-program","integrated-data","integrated-functions","integrated-trap"],default="preprocess")
    parser.add_argument("--newlib",type=Path,help="guest assembler C runtime for copy-compile")
    parser.add_argument("--resume",action="store_true")
    parser.add_argument("--timeout",type=float,default=300)
    parser.add_argument("--trace-channels",action="store_true")
    parser.add_argument("--segment-ticks",type=int,default=100000)
    parser.add_argument("--execution-name",default="space")
    parser.add_argument("--checkpoint-from",type=Path)
    args=parser.parse_args()
    if args.segment_ticks<1:parser.error("--segment-ticks must be positive")
    if args.resume and args.checkpoint_from:parser.error("choose resume or checkpoint-from")
    if args.execution_name in ("", ".", "..") or Path(args.execution_name).name!=args.execution_name:parser.error("execution-name must be a folder name")
    reuse=args.resume or args.checkpoint_from is not None
    image=args.image.resolve(); manifest=json.loads((image/"image.json").read_text())
    if args.mode=="copy-compile":
        if not args.newlib or manifest.get("target")!="copyspace-unknown-elf" or not manifest.get("framed_output"):
            raise ValueError("copy-compile requires copyspace framed image and --newlib")
    if args.mode=="integrated-copy" and not manifest.get("copy_output"):
        raise ValueError("integrated-copy requires an image prepared with --copy-output")
    if args.mode in ("integrated-program","integrated-data","integrated-functions","integrated-trap") and not manifest.get("copy_program_bytes"):
        raise ValueError("program modes require a current --copy-output image")
    profiles={2*1024*1024:"space",64*1024*1024:"space-64m",256*1024*1024:"space-256m"}
    emulator=args.emulator.resolve() if args.emulator else ROOT/"build/bin"/profiles[manifest["space_bytes"]]
    if not emulator.is_file(): raise ValueError("build matching emulator: "+str(emulator))
    if digest(image/"gcc.stream")!=manifest["stream_sha256"]: raise ValueError("image changed")
    root=args.artifacts.resolve(); root.mkdir(parents=True,exist_ok=reuse)
    configuration={"image_sha256":manifest["stream_sha256"],"mode":args.mode}
    if reuse:
        assert json.loads((root/"test-configuration.json").read_text())==configuration, "changed test image/mode"
    else:
        (root/"test-configuration.json").write_text(json.dumps(configuration)+"\n")
    if not reuse:
        files=[(b"main.c",b'#include "value.h"\n#define BASE 3\nunsigned value(void) { return BASE + VALUE; }\n'),
               (b"include/value.h",b"#define VALUE 4\n")]
        oracle=b"unsigned value(void) { return 3 + 4; }\n"
        if args.mode in ("copy-compile","integrated-copy"):
            files=[(b"main.c",b'#include "value.h"\nunsigned value(unsigned a, unsigned b) { return (a + b) ^ VALUE; }\n'),
                   (b"include/value.h",b"#define VALUE 5\n")]
            oracle=b"unsigned value(unsigned a, unsigned b) { return (a + b) ^ 5; }\n"
        elif args.mode=="integrated-program":
            files=[(b"main.c",b'#include "value.h"\n'
                b'__attribute__((noinline,noipa)) unsigned helper(unsigned a,unsigned b) { return a+b; }\n'
                b'unsigned value(unsigned a,unsigned b) { return helper(a,b)+VALUE; }\n'),
                (b"include/value.h",b"#define VALUE 1\n")]
            oracle=(b'__attribute__((noinline,noipa)) unsigned helper(unsigned a,unsigned b) { return a+b; }\n'
                b'unsigned value(unsigned a,unsigned b) { return helper(a,b)+1; }\n')
        elif args.mode=="integrated-data":
            oracle=(b'volatile unsigned char values[16384] = {3};\n'
                b'unsigned value(unsigned a, unsigned b) { values[16383] = b; return values[0] + values[16383]; }\n')
            files=[(b"main.c",oracle)]
        elif args.mode=="integrated-trap":
            oracle=b'unsigned value(unsigned a,unsigned b) { __builtin_trap(); }\n'
            files=[(b"main.c",oracle)]
        elif args.mode=="integrated-functions":
            oracle=b''.join((
                '__attribute__((noinline,noipa)) unsigned f%d(unsigned a) { return a+1; }\n'%i
                ).encode() for i in range(40))
            oracle+=b'unsigned value(unsigned a,unsigned b) {\n'
            oracle+=b''.join(('a=f%d(a);\n'%i).encode() for i in range(40))
            oracle+=b'return a; }\n'
            files=[(b"main.c",oracle)]
        for name,data in files:
            path=root/"native-inputs"/name.decode()
            path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
        native=["gcc","-E","-P","-nostdinc","-Iinclude","main.c"]
        (root/"native-command.json").write_text(json.dumps(native)+"\n")
        expected=subprocess.run(native,cwd=root/"native-inputs",capture_output=True)
        (root/"native.out").write_bytes(expected.stdout); (root/"native.err").write_bytes(expected.stderr)
        if expected.returncode or expected.stdout!=oracle:
            raise RuntimeError("native oracle differs from independent expected output")
        packet=b"\0CCFILES1"+struct.pack("<III",len(files),0,1)+struct.pack("<I",7)+b"include"
        for name,data in files:
            packet+=struct.pack("<II",len(name),len(data))+name+data
        argv=[b"cc1",b"-E",b"-P",b"-quiet",b"-nostdinc",b"-Iinclude",b"main.c"]
        if args.mode=="compile":
            argv=[b"cc1",b"-quiet",b"-O2",b"-nostdinc",b"-Iinclude",b"-march=rv32i",b"-mabi=ilp32",
                  b"-mno-relax",b"-o",b"-",b"main.c"]
            if manifest.get("framed_output"):
                argv.insert(1,b"--space-result=result.s")
                argv[argv.index(b"-o")+1]=b"result.s"
        elif args.mode in ("copy-compile","integrated-copy","integrated-program","integrated-data","integrated-functions","integrated-trap"):
            argv=[b"cc1",b"--space-result=result.s",b"-quiet",b"-O2",b"-nostdinc",b"-Iinclude",
                  b"-o",b"result.s",b"main.c"]
            if args.mode in ("integrated-copy","integrated-program","integrated-data","integrated-functions","integrated-trap"):
                option=b"--space-copy=result.s" if args.mode=="integrated-copy" else b"--space-program=result.s"
                argv[1:2]=[option,b"--space-entry=value",b"--space-arg=3",b"--space-arg=4"]
                if args.mode=="integrated-data":
                    argv.insert(5,b"--space-memory=65536")
        job=b"GCCJOB1\0"+struct.pack("<II",len(argv),len(packet))
        for arg in argv: job+=struct.pack("<I",len(arg))+arg
        job+=packet
        (root/"job.bin").write_bytes(job)
        (root/"argv.json").write_text(json.dumps([a.decode() for a in argv])+"\n")
        with (root/"in.bin").open("wb") as target, (image/"gcc.stream").open("rb") as source:
            while block:=source.read(1024*1024): target.write(block)
            target.write(job)
    print("Executing actual cc1 through primitive Space:",args.mode,flush=True)
    execution_folder=root/args.execution_name
    execution=execute_segments(emulator,execution_folder,root/"in.bin",
        space_bytes=manifest["space_bytes"],layer_bytes=manifest["layer_bits"]//8,
        ticks=args.segment_ticks,timeout=args.timeout,compression="zstd",resume=args.resume,
        channels_only=args.trace_channels,fork_from=args.checkpoint_from)
    output=(execution_folder/"program.in").read_bytes()
    raw=(execution_folder/"space.bin").read_bytes()
    def word(at,buffer=raw):
        return sum(((buffer[(at+i)//8]>>(7-(at+i)%8))&1)<<i for i in range(32))
    status,code=word(132128),word(132160)
    evidence={"scope":"actual guest cc1 "+args.mode+"; copy backend still required",
        "image_sha256":manifest["stream_sha256"],"elf_sha256":manifest["elf_sha256"],
        "job_sha256":digest(root/"job.bin"),"in_sha256":digest(root/"in.bin"),
        "guest_status":status,"guest_exit":code,"output_hex":output.hex(),
        "native_output_sha256":digest(root/"native.out"),**execution}
    (root/"evidence.json").write_text(json.dumps(evidence,indent=2)+"\n")
    assert status==10 and code==0,(status,code,output)
    assert raw[:manifest["layer_bits"]//8]==bytes(manifest["layer_bits"]//8)
    if manifest.get("framed_output"):
        assert len(output)>=24 and output[:8]==b"GCCOUT1\0",output
        result,outsize,errsize,filesize=struct.unpack_from("<IIII",output,8)
        assert result==code and len(output)==24+outsize+errsize+filesize
        stdout=output[24:24+outsize]
        stderr=output[24+outsize:24+outsize+errsize]
        file=output[24+outsize+errsize:]
        assert not stderr,stderr
        output=file if args.mode!="preprocess" else stdout
        (root/"result.bin").write_bytes(output)
    if args.mode=="preprocess":
        assert output==(root/"native.out").read_bytes(),output
        print("OK actual cc1 in Space: full preprocessed output matches GCC; guest exit 0",flush=True)
    elif args.mode in ("integrated-copy","integrated-program","integrated-data","integrated-functions","integrated-trap"):
        expected_value={"integrated-copy":2,"integrated-program":8,"integrated-data":7,"integrated-functions":43,"integrated-trap":None}[args.mode]
        key="copy_image_bytes" if args.mode=="integrated-copy" else "copy_program_bytes"
        assert len(output)==manifest[key]
        direct=root/"direct";direct.mkdir();(direct/"image.bin").write_bytes(output)
        command=[str(emulator),"--ticks","100000","--core",str(direct/"image.bin"),"--trace",str(direct/"trace.txt")]
        (direct/"command.json").write_text(json.dumps(command)+"\n")
        checked=subprocess.run(command,capture_output=True,check=True,timeout=10)
        (direct/"out.bin").write_bytes(checked.stdout)
        assert not checked.stderr and checked.stdout==(b"" if expected_value is None else struct.pack("<I",expected_value))
        assert (direct/"trace.txt").read_bytes().endswith(b" idle\n")
        evidence.update({"scope":"GNU C and copy lowering in one Space execution; direct result without RV32I",
            "direct_image_sha256":digest(direct/"image.bin"),"direct_output_hex":checked.stdout.hex()})
        (root/"evidence.json").write_text(json.dumps(evidence,indent=2)+"\n")
        print(f"OK cc1 and copy lowering in the same Space execution; direct result {expected_value}",flush=True)
    elif args.mode=="copy-compile":
        assembly=root/"guest-result.s"; assembly.write_bytes(output)
        command=[sys.executable,str(ROOT/"tests/test_gcc_copy_link.py"),"--artifacts",str(root/"copy-link"),
                 "--compiler",manifest["compiler"],"--newlib",str(args.newlib.resolve()),"--assembly",str(assembly)]
        (root/"copy-link-command.json").write_text(json.dumps(command)+"\n")
        subprocess.run(command,check=True)
        linked=json.loads((root/"copy-link/evidence.json").read_text())
        assert linked["guest_exit"]==0 and linked["direct_output_hex"]=="02000000"
        evidence.update({"scope":"GNU C compiled and lowered in Space; direct copy result without RV32I",
            "assembly_sha256":digest(assembly),"copy_link_evidence":linked})
        (root/"evidence.json").write_text(json.dumps(evidence,indent=2)+"\n")
        print("OK actual cc1 and assembler in Space; direct copies returned 2",flush=True)
    else:
        assembly=root/"guest-result.s"; assembly.write_bytes(output)
        driver=root/"control-driver.S"
        driver.write_text(""".option norvc
.option norelax
.text
.global main
main:
    addi sp, sp, -16
    sw ra, 12(sp)
    call value
    li t0, 7
    bne a0, t0, 1f
    addi a0, a0, 48
    sb a0, 0(sp)
    li t0, 10
    sb t0, 1(sp)
    mv a0, sp
    li a1, 2
    call cs_write
    li a0, 0
    lw ra, 12(sp)
    addi sp, sp, 16
    ret
1:
    li a0, 88
    call cs_exit
""")
        control=build([assembly,driver],root/"control.stream",compiler=manifest["compiler"],stream=True)
        checked=execute_segments(ROOT/"build/bin/space",root/"control",root/"control.stream",
            space_bytes=control["space_bytes"],layer_bytes=control["layer_bits"]//8,
            ticks=100000,timeout=300,compression="zstd")
        control_raw=(root/"control/space.bin").read_bytes()
        control_output=(root/"control/program.in").read_bytes()
        assert word(132128,control_raw)==10 and word(132160,control_raw)==0
        assert control_output==b"7\n",control_output
        evidence.update({"assembly_sha256":digest(assembly),"control_execution":checked,
            "control_output_hex":control_output.hex(),"control_guest_exit":word(132160,control_raw),
            "control_link_scope":"host preparation assembles guest-generated assembly; not guest linker"})
        (root/"evidence.json").write_text(json.dumps(evidence,indent=2)+"\n")
        print("OK actual cc1 compiled C in Space; generated RV32I code ran in Space and returned 7",flush=True)


if __name__=="__main__": main()
