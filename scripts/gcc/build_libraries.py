"""Cross-build actual GCC host libraries for the RV32I guest environment."""
import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"modules"))
from rv32i_toolchain import Toolchain


def run(folder, label, command, environment):
    if (folder/(label+".json")).exists():
        attempt=1
        while (folder/(label+"-"+str(attempt)+".json")).exists():
            attempt+=1
        label=label+"-"+str(attempt)
    record = {"args": command, "cwd": str(folder), "environment": {k: environment[k]
              for k in ("CC", "CXX", "AR", "RANLIB", "CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "LIBS", "PATH",
                        "HOST_LIBS", "CC_FOR_BUILD", "CXX_FOR_BUILD", "CFLAGS_FOR_BUILD", "CXXFLAGS_FOR_BUILD",
                        "CPPFLAGS_FOR_BUILD", "LDFLAGS_FOR_BUILD", "LD_FOR_BUILD", "AS_FOR_BUILD",
                        "AR_FOR_BUILD", "RANLIB_FOR_BUILD") if k in environment}}
    (folder/(label+".json")).write_text(json.dumps(record, indent=2)+"\n")
    with (folder/(label+".stdout")).open("wb") as out, (folder/(label+".stderr")).open("wb") as err:
        p = subprocess.run(command, cwd=folder, env=environment, stdout=out, stderr=err)
    (folder/(label+".status.json")).write_text(json.dumps({"returncode": p.returncode})+"\n")
    if p.returncode:
        raise RuntimeError(label+" failed; see "+str(folder/(label+".stderr")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--newlib", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--compiler")
    parser.add_argument("--start-stage", choices=["gmp", "mpfr", "mpc", "libstdcxx"], default="gmp")
    args = parser.parse_args()
    store, work = args.store.resolve(), args.work.resolve()
    work.mkdir(parents=True, exist_ok=args.start_stage!="gmp")
    newlib = args.newlib.resolve()/"riscv64-unknown-elf"
    tools = Toolchain(args.compiler)
    tool_prefix = tools.compiler[:-3]
    environment = os.environ.copy()
    environment["PATH"] = str(Path(tools.compiler).parent)+os.pathsep+environment["PATH"]
    environment["CC"] = shlex.join([tools.compiler]+tools.flags+["-nostdlib"])
    environment["CXX"] = shlex.join([tool_prefix+"g++"]+tools.flags+["-nostdlib"])
    environment["AR"], environment["RANLIB"] = tool_prefix+"ar", tool_prefix+"ranlib"
    flags = "-O2 -g -march=rv32i -mabi=ilp32 -mno-relax -msmall-data-limit=0 -ffunction-sections -fdata-sections"
    environment["CFLAGS"] = flags
    environment["CXXFLAGS"] = flags+" -fno-exceptions -fno-rtti -fno-threadsafe-statics"
    environment["CPPFLAGS"] = shlex.join(["-isystem", str(newlib/"include")])
    # Keep all conftest references live: section collection without a real
    # startup can incorrectly make absent library functions appear available.
    environment["LDFLAGS"] = shlex.join(["-nostdlib", "-L"+str(newlib/"lib"), "-Wl,-e,main"])
    environment["LIBS"] = ""
    support = work/"support"
    support.mkdir(exist_ok=args.start_stage!="gmp")
    objects = []
    for name in ("runtime/rv32i/runtime.c", "runtime/gcc/syscalls.c", "runtime/gcc/files.c"):
        obj = support/(Path(name).stem+".o")
        command = [tools.compiler]+tools.flags+shlex.split(flags)+[
            "-isystem", str(newlib/"include"), "-I"+str(ROOT/"runtime/rv32i"),
            "-DCS_RUNTIME_EXTERNAL_MEMORY", "-ffreestanding", "-fno-builtin", "-c", str(ROOT/name), "-o", str(obj)]
        run(support, obj.stem+"-compile", command, environment)
        objects.append(str(obj))
    run(support, "archive", [environment["AR"], "rcs", str(support/"libspace.a")]+objects, environment)
    base_libraries = [str(support/"libspace.a"), str(newlib/"lib/libc.a"),
                      str(newlib/"lib/libm.a"), "-lgcc"]
    install = work/"install"
    definitions = [
        ("gmp", store/"gmp-6.2.1", ["--disable-assembly"]),
        ("mpfr", store/"mpfr-4.1.0", ["--with-gmp="+str(install)]),
        ("mpc", store/"mpc-1.2.1", ["--with-gmp="+str(install), "--with-mpfr="+str(install)]),
        ("libstdcxx", store/"gcc-12.5.0/libstdc++-v3", ["--disable-multilib",
         "--with-newlib", "--disable-libstdcxx-pch", "--disable-libstdcxx-threads"]),
    ]
    stage_names=[row[0] for row in definitions]
    for name, source, extra in definitions:
        if stage_names.index(name)<stage_names.index(args.start_stage):
            status=work/(name+"-build/install.status.json")
            if not status.is_file() or json.loads(status.read_text())["returncode"]!=0:
                raise RuntimeError("cannot reuse uncompleted stage "+name)
            if not (install/"lib"/("lib"+name+".a")).is_file():
                raise RuntimeError("missing installed archive for "+name)
            continue
        dependencies = []
        if name in ("mpfr", "mpc", "libstdcxx"):
            dependencies.append(str(install/"lib/libgmp.a"))
        if name in ("mpc", "libstdcxx"):
            dependencies.insert(0, str(install/"lib/libmpfr.a"))
        environment["LIBS"] = shlex.join(["-Wl,--start-group"]+dependencies+
                                         base_libraries+["-Wl,--end-group"])
        folder = work/(name+"-build")
        folder.mkdir(exist_ok=args.start_stage!="gmp")
        command = [str(source/"configure"), "--host=riscv32-unknown-elf",
                   "--prefix="+str(install), "--disable-shared"]+extra
        run(folder, "configure", command, environment)
        run(folder, "make", ["make", "-j1"], environment)
        run(folder, "install", ["make", "-j1", "install"], environment)
        print("Prepared", name, "for RV32I/ILP32", flush=True)
    archives={}
    for path in [install/"lib"/name for name in
                 ("libgmp.a","libmpfr.a","libmpc.a","libstdc++.a","libsupc++.a")]+[support/"libspace.a"]:
        with path.open("rb") as stream:
            archives[str(path.relative_to(work))]=hashlib.file_digest(stream,"sha256").hexdigest()
    (work/"libraries.json").write_text(json.dumps({"architecture": "RV32I/ILP32", "archives_sha256":archives,
        "prefix": str(install), "compiler": tools.compiler,
        "scope": "host image preparation only; GCC guest execution still required"}, indent=2)+"\n")


if __name__ == "__main__":
    main()
