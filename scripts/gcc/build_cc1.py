"""Prepare actual GCC cc1 for RV32I execution; user C is not compiled here."""
import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from build_libraries import run, Toolchain, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--newlib", type=Path, required=True)
    parser.add_argument("--libraries", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--compiler", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    work=args.work.resolve()
    work.mkdir(parents=True, exist_ok=args.resume)
    source=args.store.resolve()/"gcc-12.5.0"
    newlib=args.newlib.resolve()/"riscv64-unknown-elf"
    libraries=args.libraries.resolve()
    receipt=json.loads((libraries/"libraries.json").read_text())
    if receipt["architecture"]!="RV32I/ILP32":
        raise ValueError("wrong library architecture")
    for name,expected in receipt["archives_sha256"].items():
        with (libraries/name).open("rb") as stream:
            if hashlib.file_digest(stream,"sha256").hexdigest()!=expected:
                raise ValueError("dependency changed: "+name)
    install=libraries/"install"
    cpp=install/"include/c++/12.5.0"
    for path in (cpp/"vector",cpp/"riscv32-unknown-elf/bits/c++config.h",
                 install/"lib/libstdc++.a",libraries/"support/libspace.a"):
        if not path.is_file(): raise ValueError("missing dependency "+str(path))
    tools=Toolchain(args.compiler)
    env=os.environ.copy()
    env["PATH"]=str(Path(tools.compiler).parent)+os.pathsep+env["PATH"]
    env["CC"]=shlex.join([tools.compiler]+tools.flags+["-nostdlib"])
    env["CXX"]=shlex.join([tools.compiler[:-3]+"g++"]+tools.flags+["-nostdlib", "-nostdinc++",
        "-isystem",str(cpp),"-isystem",str(cpp/"riscv32-unknown-elf"),"-isystem",str(cpp/"backward")])
    env["AR"],env["RANLIB"]=tools.compiler[:-3]+"ar",tools.compiler[:-3]+"ranlib"
    flags="-O2 -march=rv32i -mabi=ilp32 -mno-relax -msmall-data-limit=0 -ffunction-sections -fdata-sections"
    # Top-level GCC also forwards CXXFLAGS to native build-libcpp. Put the
    # architecture switches into guest drivers, keeping shared flags native-safe.
    architecture=["-march=rv32i","-mabi=ilp32","-mno-relax","-msmall-data-limit=0"]
    guest_includes=["-I"+str(ROOT/"runtime/gcc/include"),"-isystem",str(newlib/"include")]
    env["CC"]+=" "+shlex.join(architecture+guest_includes)
    env["CXX"]+=" "+shlex.join(architecture+guest_includes)
    env["CFLAGS"]="-O2 -ffunction-sections -fdata-sections"
    env["CXXFLAGS"]=env["CFLAGS"]+" -fno-exceptions -fno-rtti -fno-threadsafe-statics"
    env["CPPFLAGS"]=shlex.join(["-isystem",str(newlib/"include")])
    env["LDFLAGS"]="-nostdlib -Wl,-e,main"
    env["LIBS"]=shlex.join(["-Wl,--start-group"]+
        [str(install/"lib"/name) for name in ("libstdc++.a","libsupc++.a","libmpc.a","libmpfr.a","libgmp.a")]+
        [str(libraries/"support/libspace.a"),str(newlib/"lib/libc.a"),str(newlib/"lib/libm.a"),
         "-lgcc","-Wl,--end-group"])
    objects=[]
    for name in ("cxx", "files", "directories"):
        obj=work/(name+"-runtime.o")
        run(work,name+"-runtime-compile",[tools.compiler]+tools.flags+shlex.split(flags)+[
            "-isystem",str(newlib/"include"),"-c",str(ROOT/"runtime/gcc"/(name+".c")),"-o",str(obj)],env)
        objects.append(str(obj))
    env["LIBS"]=shlex.join(objects)+" "+env["LIBS"]
    # LIBS is inherited by GCC's recursive native configure. Keep it empty
    # and add guest archives only through the guest preparation drivers.
    drivers=work/"guest-drivers.json"
    drivers.write_text(json.dumps({"c":shlex.split(env["CC"]),"c++":shlex.split(env["CXX"]),
                                  "libraries":shlex.split(env["LIBS"])},indent=2)+"\n")
    wrapper=ROOT/"scripts/gcc/guest_compiler.py"
    env["CC"]=shlex.join([sys.executable,str(wrapper),str(drivers),"c"])
    env["CXX"]=shlex.join([sys.executable,str(wrapper),str(drivers),"c++"])
    env["LIBS"],env["HOST_LIBS"]="",""
    env["CC_FOR_BUILD"],env["CXX_FOR_BUILD"]="gcc","g++"
    env["CFLAGS_FOR_BUILD"],env["CXXFLAGS_FOR_BUILD"]="-O2","-O2"
    env["CPPFLAGS_FOR_BUILD"],env["LDFLAGS_FOR_BUILD"]="",""
    env["LD_FOR_BUILD"],env["AS_FOR_BUILD"],env["AR_FOR_BUILD"]="ld","as","ar"
    env["RANLIB_FOR_BUILD"]="ranlib"
    build=subprocess.run([str(source/"config.guess")],capture_output=True,check=True).stdout.decode().strip()
    configure=[str(source/"configure"),"--build="+build,"--host=riscv32-unknown-elf",
        "--target=riscv32-unknown-elf","--prefix="+str(work/"install"),"--enable-languages=c",
        "--disable-bootstrap","--disable-multilib","--disable-nls","--disable-werror",
        "--disable-checking","--disable-lto","--disable-libcc1","--disable-libsanitizer",
        "--disable-libssp","--disable-libquadmath","--disable-libgomp","--without-isl",
        "--without-headers","--with-newlib","--with-arch=rv32i","--with-abi=ilp32",
        "--with-gmp="+str(install),"--with-mpfr="+str(install),"--with-mpc="+str(install)]
    run(work,"configure",configure,env)
    run(work,"make-libraries",["make","-j1","all-build-libiberty","all-build-libcpp",
        "all-libiberty","all-libcpp","all-libdecnumber","all-libbacktrace","all-zlib",
        "all-intl","configure-gcc"],env)
    run(work,"make-cc1",["make","-C","gcc","-j1","cc1","CC_FOR_BUILD=gcc","CXX_FOR_BUILD=g++",
        "CFLAGS_FOR_BUILD=-O2","CXXFLAGS_FOR_BUILD=-O2","LDFLAGS_FOR_BUILD=","CPPFLAGS="],env)
    cc1=work/"gcc/cc1"
    with cc1.open("rb") as stream:
        checksum=hashlib.file_digest(stream,"sha256").hexdigest()
    (work/"cc1.json").write_text(json.dumps({"compiler":tools.compiler,"build":build,
        "host":"RV32I/ILP32","target":"RV32I/ILP32 (control only)","cc1":str(cc1),
        "bytes":cc1.stat().st_size,"sha256":checksum,
        "scope":"image preparation only; execution in Space not yet proven"},indent=2)+"\n")
    print("Prepared actual RV32I cc1:",cc1,flush=True)


if __name__=="__main__":
    main()
