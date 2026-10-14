"""Prepare RV32I newlib for the guest compiler; all work lives in --work."""
import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"modules"))
from rv32i_toolchain import Toolchain

NEWLIB_SHA256 = "33f12605e0054965996c25c1382b3e463b0af91799001f5bb8c0630f2ec8c852"


def strong_atexit(store, work, tools, environment):
    prefix=work/"newlib-install/riscv64-unknown-elf"
    library=prefix/"lib/libc.a"
    source=store/"newlib-4.5.0.20241231/newlib/libc/stdlib/__atexit.c"
    if "#if !defined (_ATEXIT_DYNAMIC_ALLOC) || !defined (MALLOC_PROVIDED)" not in source.read_text():
        raise ValueError("unexpected upstream atexit implementation")
    if "#define _ATEXIT_DYNAMIC_ALLOC 1" not in (prefix/"include/newlib.h").read_text():
        raise ValueError("dynamic atexit is not enabled")
    folder=work/"atexit-provider"
    attempt=1
    while folder.exists():
        folder=work/("atexit-provider-"+str(attempt)); attempt+=1
    folder.mkdir()
    if (work/"newlib.json").is_file(): shutil.copy2(work/"newlib.json",folder/"newlib-before.json")
    original=folder/"libc-original.a"; shutil.copy2(library,original)
    flags=shlex.split(environment["CFLAGS_FOR_TARGET"])
    objects=[]
    for name in ("__atexit","__call_atexit"):
        frozen=folder/(name+".c"); frozen.write_bytes((source.parent/(name+".c")).read_bytes())
        obj=folder/("libc_a-"+name+".o")
        run(folder,name+"-compile",[tools.compiler]+tools.flags+flags+[
            "-D_COMPILING_NEWLIB","-DMALLOC_PROVIDED","-isystem",str(prefix/"include"),
            "-I"+str(source.parent),"-c",str(frozen),"-o",str(obj)],environment)
        objects.append(str(obj))
    ar=tools.compiler[:-3]+"ar"
    members=subprocess.run([ar,"t",str(library)],capture_output=True,check=True).stdout.splitlines()
    if any(members.count(Path(obj).name.encode())!=1 for obj in objects):
        raise ValueError("unexpected atexit archive members")
    run(folder,"archive",[ar,"rcs",str(library)]+objects,environment)
    with original.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def run(folder, label, command, environment):
    (folder/(label+".json")).write_text(json.dumps({"args": command,
        "cwd": str(folder), "environment": {k: environment[k] for k in
        ("CC_FOR_TARGET", "CXX_FOR_TARGET", "CFLAGS_FOR_TARGET", "CXXFLAGS_FOR_TARGET", "PATH")}}, indent=2)+"\n")
    with (folder/(label+".stdout")).open("wb") as out, (folder/(label+".stderr")).open("wb") as err:
        process = subprocess.run(command, cwd=folder, env=environment, stdout=out, stderr=err)
    (folder/(label+".status.json")).write_text(json.dumps({"returncode": process.returncode})+"\n")
    if process.returncode:
        raise RuntimeError(label+" failed; see "+str(folder/(label+".stderr")))


def build(store, work, compiler=None):
    store, work = store.resolve(), work.resolve()
    source = store/"newlib-4.5.0.20241231"
    archive = store/"newlib-4.5.0.20241231.tar.gz"
    with archive.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != NEWLIB_SHA256:
            raise ValueError("newlib source archive checksum mismatch")
    tools = Toolchain(compiler)
    triple = "riscv64-unknown-elf"
    folder, prefix = work/"newlib-build", work/"newlib-install"
    if folder.exists():
        raise ValueError("build directory exists; inspect the previous build before retrying")
    folder.mkdir(parents=True)
    environment = os.environ.copy()
    environment["PATH"] = str(Path(tools.compiler).parent)+os.pathsep+environment["PATH"]
    environment["CC_FOR_TARGET"] = shlex.join([tools.compiler]+tools.flags)
    environment["CXX_FOR_TARGET"] = shlex.join([tools.compiler[:-3]+"g++"]+tools.flags)
    flags = "-O2 -g -march=rv32i -mabi=ilp32 -mno-relax -msmall-data-limit=0 -ffunction-sections -fdata-sections -DMALLOC_ALIGNMENT=16"
    environment["CFLAGS_FOR_TARGET"] = flags
    environment["CXXFLAGS_FOR_TARGET"] = flags
    command = [str(source/"configure"), "--target="+triple, "--prefix="+str(prefix),
        "--disable-multilib", "--disable-libgloss", "--disable-newlib-supplied-syscalls",
        "--disable-newlib-multithread", "--enable-newlib-io-c99-formats",
        "--enable-newlib-io-long-long", "--enable-newlib-io-long-double",
        "--enable-newlib-atexit-dynamic-alloc"]
    run(folder, "configure", command, environment)
    run(folder, "make", ["make", "-j1", "all-target-newlib"], environment)
    run(folder, "install", ["make", "-j1", "install-target-newlib"], environment)
    original_digest=strong_atexit(store,work,tools,environment)
    library = prefix/triple/"lib/libc.a"
    with library.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    result = {"source_sha256": NEWLIB_SHA256, "compiler": tools.compiler,
              "architecture": "RV32I/ILP32", "prefix": str(prefix),
              "libc_bytes": library.stat().st_size, "libc_sha256": digest,
              "libc_before_strong_atexit_sha256":original_digest,
              "scope": "host preparation only; guest execution not yet proven"}
    (work/"newlib.json").write_text(json.dumps(result, indent=2)+"\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--compiler")
    parser.add_argument("--repair-atexit",action="store_true",help="finish an existing completed unpatched build")
    args = parser.parse_args()
    if args.repair_atexit:
        store,work=args.store.resolve(),args.work.resolve()
        result=json.loads((work/"newlib.json").read_text())
        tools=Toolchain(args.compiler)
        if tools.compiler!=result["compiler"]: raise ValueError("use recorded preparation compiler")
        library=work/"newlib-install/riscv64-unknown-elf/lib/libc.a"
        with library.open("rb") as stream:
            if hashlib.file_digest(stream,"sha256").hexdigest()!=result["libc_sha256"]:
                raise ValueError("existing library changed")
        environment=json.loads((work/"newlib-build/configure.json").read_text())["environment"]
        result["libc_before_strong_atexit_sha256"]=strong_atexit(store,work,tools,environment)
        with library.open("rb") as stream:
            result["libc_sha256"]=hashlib.file_digest(stream,"sha256").hexdigest()
        result["libc_bytes"]=library.stat().st_size
        (work/"newlib.json").write_text(json.dumps(result,indent=2)+"\n")
    else:
        result=build(args.store,args.work,args.compiler)
    print(json.dumps(result,indent=2),flush=True)


if __name__ == "__main__":
    main()
