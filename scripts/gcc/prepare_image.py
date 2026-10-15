"""Relink real cc1 with guest entry and encode its initial Space image."""
import argparse
import hashlib
import json
import shlex
import struct
import subprocess
import sys
import shutil
from pathlib import Path
from build_libraries import ROOT, Toolchain
from package_target_library import load_library, embedded_assembly
sys.path.insert(0,str(ROOT/"modules"))
from rv32i import Image, Layout
from rv32i_stream import encode_stream


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def run(folder,label,argv,cwd):
    (folder/(label+".json")).write_text(json.dumps({"argv":argv,"cwd":str(cwd)},indent=2)+"\n")
    result=subprocess.run(argv,cwd=cwd,capture_output=True)
    (folder/(label+".stdout")).write_bytes(result.stdout)
    (folder/(label+".stderr")).write_bytes(result.stderr)
    (folder/(label+".status.json")).write_text(json.dumps({"returncode":result.returncode})+"\n")
    if result.returncode: raise RuntimeError(label+" failed; see "+str(folder/(label+".stderr")))
    return result.stdout


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cc1-work",type=Path,required=True)
    parser.add_argument("--newlib",type=Path,required=True)
    parser.add_argument("--libraries",type=Path,required=True)
    parser.add_argument("--artifacts",type=Path,required=True)
    parser.add_argument("--compiler",required=True)
    parser.add_argument("--heap-bytes",type=lambda s:int(s,0),default=16*1024*1024)
    parser.add_argument("--memory-bytes",type=lambda s:int(s,0),default=64*1024*1024)
    parser.add_argument("--space-bytes",type=lambda s:int(s,0),default=256*1024*1024)
    parser.add_argument("--framed-output",action="store_true",help="emit GCCOUT1 with separate result/diagnostics")
    parser.add_argument("--copy-output",action="store_true",help="lower cc1 output with the guest copy assembler")
    parser.add_argument("--target-library",type=Path,help="install a verified target library package as the default runtime")
    parser.add_argument("--copy-program-bytes",type=lambda s:int(s,0),default=262144)
    parser.add_argument("--copy-label-capacity",type=int,default=32)
    parser.add_argument("--copy-jump-capacity",type=int,default=64)
    parser.add_argument("--copy-call-capacity",type=int,default=32)
    parser.add_argument("--copy-symbol-capacity",type=int,default=12)
    parser.add_argument("--copy-relocation-capacity",type=int,default=64)
    args=parser.parse_args()
    if args.target_library and not args.copy_output:
        raise ValueError("a default target library requires --copy-output")
    capacities={"label":args.copy_label_capacity,"jump":args.copy_jump_capacity,"call":args.copy_call_capacity,
                "symbol":args.copy_symbol_capacity,"relocation":args.copy_relocation_capacity}
    if any(not 1<=value<=1048576 for value in capacities.values()):
        raise ValueError("copy table capacities must be in 1..1048576")
    size=args.copy_program_bytes
    if not 262144<=size<=min(268435456,args.space_bytes) or size&(size-1):
        raise ValueError("copy program size must be a power of two fitting Space, at least 262144")
    if not args.copy_output and (size!=262144 or capacities!={"label":32,"jump":64,"call":32,"symbol":12,"relocation":64}):
        raise ValueError("copy configuration requires --copy-output")
    code_begin=60032+64*capacities["jump"]+32*capacities["call"]+32*capacities["symbol"]
    if args.copy_output and code_begin+256*(3*((args.space_bytes*8).bit_length()-1)-1)>(size-8192)*8:
        raise ValueError("copy tables leave no room for code and default data/stack memory")
    if not 0<args.heap_bytes<args.memory_bytes-4*1024*1024:
        raise ValueError("heap must leave room for code and stack")
    work=args.cc1_work.resolve(); gcc=work/"gcc"
    receipt=json.loads((work/"cc1.json").read_text())
    if args.copy_output and (not args.framed_output or receipt["target"]!="copyspace-unknown-elf"):
        raise ValueError("--copy-output requires --framed-output and copyspace cc1")
    if digest(gcc/"cc1")!=receipt["sha256"]: raise ValueError("original cc1 changed")
    target_archive=target_receipt=None
    if args.target_library:
        target_archive,target_receipt=load_library(args.target_library.resolve(),
            receipt["build_profile"]["target_sources_sha256"]["gcc/config/copyspace/copyspace.h"])
    root=args.artifacts.resolve(); root.mkdir(parents=True,exist_ok=False)
    tools=Toolchain(args.compiler)
    if tools.compiler!=receipt["compiler"]: raise ValueError("use the recorded cc1 preparation compiler")
    newlib=args.newlib.resolve()/"riscv64-unknown-elf"
    libraries=args.libraries.resolve()
    library_receipt=json.loads((libraries/"libraries.json").read_text())
    for name,expected in library_receipt["archives_sha256"].items():
        if digest(libraries/name)!=expected: raise ValueError("library changed: "+name)
    sources=root/"sources"
    frozen={}
    generated={}
    names=["runtime/gcc/"+name for name in ("start.S","link.ld","main.c","job.c","job.h",
        "files.c","files.h","directories.c","include/dirent.h","syscalls.c","cxx.c")]
    names += ["runtime/rv32i/runtime.c","runtime/rv32i/copy_space.h","runtime/copy_c/input_files.h"]
    if args.framed_output: names.extend(["runtime/gcc/response.c","runtime/gcc/response.h"])
    if args.copy_output: names.extend(["runtime/gcc/"+name for name in ("copy_link.c","copy_link.h","copy_emit.c","copy_emit.h")])
    if target_archive:
        shutil.copyfile(target_archive,root/"target-libgcc.a")
        if digest(root/"target-libgcc.a")!=target_receipt["archive_sha256"]:
            raise ValueError("target archive changed during preparation")
        (root/"target-library.json").write_text(json.dumps(target_receipt,indent=2)+"\n")
        name="runtime/gcc/target_archive.S"
        generated[name]=embedded_assembly("target-libgcc.a",(root/"target-libgcc.a").stat().st_size)
        names.append(name)
    for name in names:
        path=sources/name; path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(generated[name] if name in generated else (ROOT/name).read_bytes()); frozen[name]=digest(path)
    objects=[]
    for name in [n for n in names if n.endswith((".c",".S"))]:
        path=sources/name
        obj=root/(path.stem+".o")
        command=[tools.compiler]+tools.flags+["-O2","-march=rv32i","-mabi=ilp32","-mno-relax",
            "-msmall-data-limit=0","-ffunction-sections","-fdata-sections","-fno-pic",
            "-fno-stack-protector","-DCS_RUNTIME_EXTERNAL_MEMORY","-DCS_GCC_HEAP_BYTES="+str(args.heap_bytes),
            "-DCS_GCC_MEMORY_BYTES="+str(args.memory_bytes),
            "-isystem",str(newlib/"include"),"-I"+str(sources/"runtime/gcc"),
            "-I"+str(sources/"runtime/rv32i"),"-c",str(path),"-o",str(obj)]
        if args.framed_output: command.insert(1,"-DCS_GCC_FRAMED_OUTPUT")
        if args.copy_output: command[1:1]=["-DCS_GCC_COPY_OUTPUT",
            "-DCS_GCC_COPY_ADDRESS_BITS="+str((args.space_bytes*8).bit_length()-1),
            "-DCS_GCC_COPY_PROGRAM_BYTES="+str(args.copy_program_bytes)]+[
                "-DCS_COPY_"+name.upper()+"_CAPACITY="+str(value) for name,value in capacities.items()]
        run(root,path.stem+"-compile",command,root); objects.append(str(obj))
    dry=run(root,"link-recipe",["make","-n","-C",str(gcc),"-W","cc1-checksum.o","cc1",
        "CC_FOR_BUILD=gcc","CXX_FOR_BUILD=g++","CPPFLAGS="],work)
    candidates=[]
    for line in dry.decode().replace("\\\n"," ").splitlines():
        words=shlex.split(line)
        if "-o" in words and words[words.index("-o")+1]=="cc1" and "c++" in words:
            candidates.append(words)
    if len(candidates)!=1: raise ValueError("cannot identify unique real cc1 link command")
    words=candidates[0]
    prefix=words.index("c++")+1
    arguments=words[prefix:]
    at=arguments.index("-o")+1
    elf=root/"gcc-space.elf"; arguments[at]=str(elf)
    arguments=[arg for arg in arguments if arg!="-Wl,-e,main"]
    driver=json.loads((work/"guest-drivers.json").read_text())["c++"]
    installed=libraries/"install/lib"
    group=["-Wl,--start-group"]+[str(installed/name) for name in
        ("libstdc++.a","libsupc++.a","libmpc.a","libmpfr.a","libgmp.a")]
    group += [str(newlib/"lib/libc.a"),str(newlib/"lib/libm.a"),"-lgcc","-Wl,--end-group"]
    link=driver+["-L"+str(newlib/"lib"),"-L"+str(installed)]+arguments+objects+group+[
        "-T",str(sources/"runtime/gcc/link.ld"),"-Wl,-e,_start","-Wl,--wrap=main","-Wl,--gc-sections",
        "-Wl,--defsym=CS_STACK_TOP="+str(args.memory_bytes-16),"-Wl,-Map="+str(root/"gcc-space.map")]
    run(root,"link",link,gcc)
    data=elf.read_bytes()
    if data[:6]!=b"\x7fELF\x01\x01" or struct.unpack_from("<I",data,24)[0]!=0:
        raise ValueError("expected ELF32 little-endian with _start at zero")
    header=struct.unpack_from("<HHIIIIIHHHHHH",data,16)
    if header[1]!=243: raise ValueError("expected RISC-V ELF")
    end=0
    for i in range(header[9]):
        segment=struct.unpack_from("<IIIIIIII",data,header[4]+i*header[8])
        if segment[0]==1: end=max(end,segment[2]+segment[5])
    if end>args.memory_bytes-4*1024*1024: raise ValueError("ELF leaves less than 4 MiB stack")
    binary=root/"gcc-space.bin"
    run(root,"objcopy",[tools.objcopy,"-O","binary",str(elf),str(binary)],root)
    image=Image(io=True,memory_bytes=args.memory_bytes,layout=Layout(args.space_bytes)).build()
    encoded,manifest=image.encode(binary.read_bytes(),registers={2:args.memory_bytes-16})
    stream,manifest=encode_stream(encoded,manifest,binary.read_bytes())
    destination=root/"gcc.stream"; destination.write_bytes(stream)
    manifest.update({"original_cc1_sha256":receipt["sha256"],"elf_sha256":digest(elf),
        "target":receipt["target"],"target_sources_sha256":receipt["build_profile"].get("target_sources_sha256"),
        "compiler":tools.compiler,"framed_output":args.framed_output,
        "copy_output":args.copy_output,"copy_image_bytes":65536 if args.copy_output else None,
        "copy_program_bytes":args.copy_program_bytes if args.copy_output else None,
        "copy_capacities":capacities if args.copy_output else None,
        "target_library":None if not target_receipt else {"archive_sha256":target_receipt["archive_sha256"],
            "catalog_sha256":target_receipt["catalog_sha256"],"units":len(target_receipt["members"]),
            "manifest_sha256":digest(root/"target-library.json"),"default":True},
        "libraries_sha256":library_receipt["archives_sha256"],
        "newlib_libc_sha256":digest(newlib/"lib/libc.a"),"newlib_libm_sha256":digest(newlib/"lib/libm.a"),
        "runtime_sources":frozen,"heap_bytes":args.heap_bytes,"elf_memory_end":end,
        "stack_reserve":args.memory_bytes-end,"stream_sha256":digest(destination),
        "scope":"real cc1 image preparation; guest execution not yet proven"})
    (root/"image.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("Prepared real cc1 Space stream:",destination,flush=True)


if __name__=="__main__": main()
