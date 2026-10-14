"""Relink real cc1 with guest entry and encode its initial Space image."""
import argparse
import hashlib
import json
import shlex
import struct
import subprocess
import sys
from pathlib import Path
from build_libraries import ROOT, Toolchain
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
    args=parser.parse_args()
    if not 0<args.heap_bytes<args.memory_bytes-4*1024*1024:
        raise ValueError("heap must leave room for code and stack")
    work=args.cc1_work.resolve(); gcc=work/"gcc"
    receipt=json.loads((work/"cc1.json").read_text())
    if digest(gcc/"cc1")!=receipt["sha256"]: raise ValueError("original cc1 changed")
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
    names=["runtime/gcc/"+name for name in ("start.S","link.ld","main.c","job.c","job.h",
        "files.c","files.h","directories.c","include/dirent.h","syscalls.c","cxx.c")]
    names += ["runtime/rv32i/runtime.c","runtime/rv32i/copy_space.h","runtime/copy_c/input_files.h"]
    for name in names:
        path=sources/name; path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes((ROOT/name).read_bytes()); frozen[name]=digest(path)
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
        "compiler":tools.compiler,"libraries_sha256":library_receipt["archives_sha256"],
        "newlib_libc_sha256":digest(newlib/"lib/libc.a"),"newlib_libm_sha256":digest(newlib/"lib/libm.a"),
        "runtime_sources":frozen,"heap_bytes":args.heap_bytes,"elf_memory_end":end,
        "stack_reserve":args.memory_bytes-end,"stream_sha256":digest(destination),
        "scope":"real cc1 image preparation; guest execution not yet proven"})
    (root/"image.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("Prepared real cc1 Space stream:",destination,flush=True)


if __name__=="__main__": main()
