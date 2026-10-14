"""Prepare RV32I newlib for the guest compiler; all work lives in --work."""
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

NEWLIB_SHA256 = "33f12605e0054965996c25c1382b3e463b0af91799001f5bb8c0630f2ec8c852"


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
        "--enable-newlib-io-long-long", "--enable-newlib-io-long-double"]
    run(folder, "configure", command, environment)
    run(folder, "make", ["make", "-j1", "all-target-newlib"], environment)
    run(folder, "install", ["make", "-j1", "install-target-newlib"], environment)
    library = prefix/triple/"lib/libc.a"
    with library.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    result = {"source_sha256": NEWLIB_SHA256, "compiler": tools.compiler,
              "architecture": "RV32I/ILP32", "prefix": str(prefix),
              "libc_bytes": library.stat().st_size, "libc_sha256": digest,
              "scope": "host preparation only; guest execution not yet proven"}
    (work/"newlib.json").write_text(json.dumps(result, indent=2)+"\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--compiler")
    args = parser.parse_args()
    print(json.dumps(build(args.store, args.work, args.compiler), indent=2), flush=True)


if __name__ == "__main__":
    main()
