"""Prepare actual GCC cc1 for RV32I execution; user C is not compiled here."""
import argparse
import hashlib
import json
import os
import shlex
import subprocess
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
    env["CFLAGS"]=flags
    env["CXXFLAGS"]=flags+" -fno-exceptions -fno-rtti -fno-threadsafe-statics"
    env["CPPFLAGS"]=shlex.join(["-isystem",str(newlib/"include")])
    env["LDFLAGS"]="-nostdlib -Wl,-e,main"
    env["LIBS"]=shlex.join(["-Wl,--start-group"]+
        [str(install/"lib"/name) for name in ("libstdc++.a","libsupc++.a","libmpc.a","libmpfr.a","libgmp.a")]+
        [str(libraries/"support/libspace.a"),str(newlib/"lib/libc.a"),str(newlib/"lib/libm.a"),
         "-lgcc","-Wl,--end-group"])
    run(work,"cxx-runtime-compile",[tools.compiler]+tools.flags+shlex.split(flags)+[
        "-c",str(ROOT/"runtime/gcc/cxx.c"),"-o",str(work/"cxx-runtime.o")],env)
    env["LIBS"]=shlex.quote(str(work/"cxx-runtime.o"))+" "+env["LIBS"]
    # GCC appends HOST_LIBS after its own archives; configure also needs LIBS.
    env["HOST_LIBS"]=env["LIBS"]
    env["CC_FOR_BUILD"],env["CXX_FOR_BUILD"]="gcc","g++"
    build=subprocess.run([str(source/"config.guess")],capture_output=True,check=True).stdout.decode().strip()
    configure=[str(source/"configure"),"--build="+build,"--host=riscv32-unknown-elf",
        "--target=riscv32-unknown-elf","--prefix="+str(work/"install"),"--enable-languages=c",
        "--disable-bootstrap","--disable-multilib","--disable-nls","--disable-werror",
        "--disable-checking","--disable-lto","--disable-libcc1","--disable-libsanitizer",
        "--disable-libssp","--disable-libquadmath","--disable-libgomp","--without-isl",
        "--without-headers","--with-newlib","--with-arch=rv32i","--with-abi=ilp32",
        "--with-gmp="+str(install),"--with-mpfr="+str(install),"--with-mpc="+str(install)]
    run(work,"configure",configure,env)
    run(work,"make",["make","-j1","all-gcc"],env)
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
