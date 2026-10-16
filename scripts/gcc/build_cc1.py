"""Prepare actual GCC cc1 for RV32I execution; user C is not compiled here."""
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from build_libraries import run, Toolchain, ROOT


def reuse_backend_build(base, work, profile, source):
    """Clone a completed build when only the target's C++ backend changed."""
    base=base.resolve()
    if work.exists() or work.is_relative_to(base) or base.is_relative_to(work):
        raise ValueError("reuse needs a separate, unused work directory")
    receipt=json.loads((base/"cc1.json").read_text())
    before=receipt["build_profile"]
    for key in ("compiler","optimization","target"):
        if before.get(key)!=profile.get(key):
            raise ValueError("cannot reuse a different compiler, optimization or target")
    if before!=json.loads((base/"build-profile.json").read_text()):
        raise ValueError("inconsistent base build profile")
    with (base/"gcc/cc1").open("rb") as stream:
        if hashlib.file_digest(stream,"sha256").hexdigest()!=receipt["sha256"]:
            raise ValueError("changed base compiler")
    old_sources=before["target_sources_sha256"]
    new_sources=profile["target_sources_sha256"]
    changed={n for n in old_sources.keys()|new_sources.keys()
             if old_sources.get(n)!=new_sources.get(n)}
    if changed!={"gcc/config/copyspace/copyspace.cc"}:
        raise ValueError("reuse requires only the copyspace C++ backend to change")
    old_source=Path(before["target_source"])
    for name,expected in old_sources.items():
        with (old_source/name).open("rb") as stream:
            if hashlib.file_digest(stream,"sha256").hexdigest()!=expected:
                raise ValueError("changed base target source: "+name)
    backend="gcc/config/copyspace/copyspace.cc"
    # The copied GC tables remain valid only for this unchanged private type.
    # Other target headers and the MD inputs were already checked bytewise.
    gc_types=[]
    for root in (old_source,source):
        text=(root/backend).read_text()
        match=re.search(r'struct GTY\(\(\)\) machine_function\s*\{.*?\n\s*\};',text,re.S)
        if text.count("GTY")!=1 or not match:
            raise ValueError("backend GC declarations need a fresh build")
        gc_types.append(match.group())
    if gc_types[0]!=gc_types[1]:
        raise ValueError("changed backend GC declarations need a fresh build")
    rule="$(out_object_file): $(out_file)\n"
    if (base/"gcc/Makefile").read_text().count(rule)!=1:
        raise ValueError("reuse needs an original backend make rule")
    # Reuse actual files, never writable hard links into the frozen base build.
    shutil.copytree(base,work,symlinks=True)
    (work/"cc1.json").rename(work/"base-cc1.json")
    (work/"build-profile.json").rename(work/"base-build-profile.json")
    replacements=[(str(base).encode(),str(work).encode())]
    for directory,_,names in os.walk(work):
        for name in names:
            path=Path(directory)/name
            if path.is_symlink() or not (name in ("Makefile","config.status","config.cache","gtyp-input.list","mddeps.mk") or
                                        path.suffix in (".Po",".Plo",".TPo",".TPlo")):
                continue
            original=path.read_bytes();updated=original
            for a,b in replacements:
                updated=updated.replace(a,b)
            if updated!=original:
                stamp=path.stat();path.write_bytes(updated)
                os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
    # Retain all unchanged source paths and generated tables. Redirect just
    # the backend compilation; relocating srcdir changes generated #line
    # paths and would unnecessarily rebuild the whole compiler.
    makefile=work/"gcc/Makefile"
    text=makefile.read_text()
    stamp=makefile.stat()
    makefile.write_text(text.replace(rule,"$(out_object_file): "+str(source/backend)+"\n"))
    os.utime(makefile,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
    (work/"build-profile.json").write_text(json.dumps(profile,indent=2)+"\n")
    (work/"reused-build.json").write_text(json.dumps({
        "base":str(base),"base_cc1_sha256":receipt["sha256"],
        "configuration_source":str(old_source),
        "gc_declaration_sha256":hashlib.sha256(gc_types[0].encode()).hexdigest(),
        "changed_target_sources":sorted(changed),
        "scope":"isolated incremental build; unchanged compiler objects copied from verified base"},indent=2)+"\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--newlib", type=Path, required=True)
    parser.add_argument("--libraries", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--compiler", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--reuse-build", type=Path, help="clone a completed build with only a C++ backend change")
    parser.add_argument("--copy-target", type=Path, help="directory prepared by prepare_target.py")
    parser.add_argument("--configure-only", action="store_true")
    parser.add_argument("--optimization",choices=["O0","O1","O2","O3","Os"],
                        help="explicit cc1 compilation optimization; requires a fresh object build")
    args = parser.parse_args()
    work=args.work.resolve()
    if args.reuse_build:
        if args.resume or not args.copy_target:
            parser.error("--reuse-build needs --copy-target and a fresh work directory")
    else:
        work.mkdir(parents=True, exist_ok=args.resume)
    source=args.store.resolve()/"gcc-12.5.0"
    target="riscv32-unknown-elf"
    target_sources=None
    if args.copy_target:
        from fetch import SHA512
        prepared=args.copy_target.resolve()
        target_receipt=json.loads((prepared/"target.json").read_text())
        if target_receipt["target"]!="copyspace-unknown-elf" or target_receipt["gcc_archive_sha512"]!=SHA512:
            raise ValueError("wrong copyspace target receipt")
        for name,expected in target_receipt["original_source_sha256"].items():
            with (source/name).open("rb") as stream:
                if hashlib.file_digest(stream,"sha256").hexdigest()!=expected:
                    raise ValueError("original target source changed: "+name)
        source=prepared/"source"
        target_sources=target_receipt["generated_source_sha256"]
        for name,expected in target_sources.items():
            with (source/name).open("rb") as stream:
                if hashlib.file_digest(stream,"sha256").hexdigest()!=expected:
                    raise ValueError("generated target source changed: "+name)
        target=target_receipt["target"]
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
    profile={"compiler":tools.compiler,"optimization":args.optimization}
    if target_sources is not None:
        profile.update(target=target,target_source=str(source),target_sources_sha256=target_sources)
    if args.reuse_build:
        reuse_backend_build(args.reuse_build,work,profile,source)
    profile_file=work/"build-profile.json"
    if profile_file.is_file():
        if json.loads(profile_file.read_text())!=profile:
            raise ValueError("build profile changed; use a fresh work directory")
    elif args.optimization and (work/"gcc").is_dir() and any((work/"gcc").rglob("*.o")):
        raise ValueError("cannot optimize existing untracked objects; use a fresh work directory")
    profile_file.write_text(json.dumps(profile,indent=2)+"\n")
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
    for name in ("cxx", "files", "directories", "syscalls"):
        obj=work/(name+"-runtime.o")
        run(work,name+"-runtime-compile",[tools.compiler]+tools.flags+shlex.split(flags)+[
            "-isystem",str(newlib/"include"),"-I"+str(ROOT/"runtime/rv32i"),
            "-c",str(ROOT/"runtime/gcc"/(name+".c")),"-o",str(obj)],env)
        objects.append(str(obj))
    env["LIBS"]=shlex.join(objects)+" "+env["LIBS"]
    # LIBS is inherited by GCC's recursive native configure. Keep it empty
    # and add guest archives only through the guest preparation drivers.
    drivers=work/"guest-drivers.json"
    driver_profile={"c":shlex.split(env["CC"]),"c++":shlex.split(env["CXX"]),
                    "libraries":shlex.split(env["LIBS"])}
    reused=(work/"reused-build.json").is_file()
    if reused:
        base=Path(json.loads((work/"reused-build.json").read_text())["base"])
        expected=json.loads((base/"guest-drivers.json").read_text())
        expected={k:[v.replace(str(base),str(work)) for v in values] for k,values in expected.items()}
        if expected!=driver_profile:
            raise ValueError("reused build needs identical compiler flags and library paths")
    drivers.write_text(json.dumps(driver_profile,indent=2)+"\n")
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
        "--target="+target,"--prefix="+str(work/"install"),"--enable-languages=c",
        "--disable-bootstrap","--disable-multilib","--disable-nls","--disable-werror",
        "--disable-checking","--disable-lto","--disable-libcc1","--disable-libsanitizer",
        "--disable-libssp","--disable-libquadmath","--disable-libgomp","--without-isl",
        "--without-headers","--with-newlib",
        "--with-gmp="+str(install),"--with-mpfr="+str(install),"--with-mpc="+str(install)]
    if target=="riscv32-unknown-elf":
        configure.extend(["--with-arch=rv32i","--with-abi=ilp32"])
    if not reused:
        run(work,"configure",configure,env)
    if args.configure_only:
        print("Configured guest cc1 target:",target,"; cc1 compilation not performed",flush=True)
        return
    if not reused:
        run(work,"make-libraries",["make","-j1","all-build-libiberty","all-build-libcpp",
            "all-libiberty","all-libcpp","all-libdecnumber","all-libbacktrace","all-zlib",
            "all-intl","configure-gcc"],env)
    cc1_make=["make","-C","gcc","-j1","cc1","CC_FOR_BUILD=gcc","CXX_FOR_BUILD=g++",
        "CFLAGS_FOR_BUILD=-O2","CXXFLAGS_FOR_BUILD=-O2","LDFLAGS_FOR_BUILD=","CPPFLAGS="]
    if args.optimization:
        for key in ("CFLAGS","CXXFLAGS"):
            shared=[flag for flag in shlex.split(env[key]) if not flag.startswith("-O")]
            cc1_make.append(key+"="+shlex.join(["-"+args.optimization]+shared))
    run(work,"make-cc1",cc1_make,env)
    cc1=work/"gcc/cc1"
    with cc1.open("rb") as stream:
        checksum=hashlib.file_digest(stream,"sha256").hexdigest()
    (work/"cc1.json").write_text(json.dumps({"compiler":tools.compiler,"build":build,
        "host":"RV32I/ILP32","target":target if target_sources is not None else "RV32I/ILP32 (control only)","cc1":str(cc1),
        "bytes":cc1.stat().st_size,"sha256":checksum,"build_profile":profile,
        "reused_build":json.loads((work/"reused-build.json").read_text()) if reused else None,
        "scope":"image preparation only; execution in Space not yet proven"},indent=2)+"\n")
    print("Prepared actual RV32I cc1:",cc1,flush=True)


if __name__=="__main__":
    main()
