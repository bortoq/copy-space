"""Prove newlib memory and stream functions execute through primitive Space."""
import argparse
import hashlib
import json
import subprocess
import sys
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts/rv32i"))
from build import build
from space_segments import execute_segments


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--newlib", type=Path, required=True, help="newlib install prefix")
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--compiler")
    parser.add_argument("--fixture", choices=["stdlib", "files", "job", "initializers"], default="stdlib")
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    source = ROOT/("tests/fixtures/gcc/"+args.fixture+".c")
    (root/"source.c").write_bytes(source.read_bytes())
    native_command = ["gcc", "-O2", "-Wall", "-Wextra", "-Werror", "-I"+str(ROOT/"runtime/gcc"), str(source)]
    if args.fixture in ("files","job"): native_command.append(str(ROOT/"runtime/gcc/files.c"))
    if args.fixture=="job": native_command.append(str(ROOT/"runtime/gcc/job.c"))
    native_command += ["-o", str(root/"native")]
    (root/"native-compile.json").write_text(json.dumps(native_command, indent=2)+"\n")
    native_build = subprocess.run(native_command, capture_output=True)
    (root/"native-compile.stderr").write_bytes(native_build.stderr)
    assert native_build.returncode == 0, native_build.stderr
    incoming = b"3 4\n"
    if args.fixture=="job":
        files=b"\0CCFILES1"+struct.pack("<III",1,0,0)+struct.pack("<II",4,3)+b"in.ca+b"
        incoming=b"GCCJOB1\0"+struct.pack("<II",3,len(files))
        incoming+=b"".join(struct.pack("<I",len(arg))+arg for arg in (b"cc1",b"",b"-E"))+files
    expected = subprocess.run([str(root/"native")], input=incoming, capture_output=True)
    (root/"native.out").write_bytes(expected.stdout)
    golden={"files":b"gcc-files:7\n", "job":b"gcc-job:7\n",
            "stdlib":b"gcc-libc:7:15:4294967303\n",
            "initializers":b"gcc-init:7\ngcc-exit:7\ngcc-fini:7\n"}[args.fixture]
    assert expected.returncode == 0 and expected.stdout == golden, expected
    prefix = args.newlib.resolve()/"riscv64-unknown-elf"
    libc, libm = prefix/"lib/libc.a", prefix/"lib/libm.a"
    flags = ["-isystem", str(prefix/"include"), "-I"+str(ROOT/"runtime/gcc"), "-DCS_RUNTIME_EXTERNAL_MEMORY",
             "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections"]
    libraries = ["-Wl,--start-group", str(libc), str(libm), "-lgcc", "-Wl,--end-group"]
    sources=[source, ROOT/"runtime/gcc/syscalls.c", ROOT/"runtime/gcc/files.c"]
    if args.fixture=="job": sources.append(ROOT/"runtime/gcc/job.c")
    start=ROOT/"runtime/gcc/start.S" if args.fixture=="initializers" else ROOT/"runtime/rv32i/start.S"
    linker=ROOT/"runtime/gcc/link.ld" if args.fixture=="initializers" else ROOT/"runtime/rv32i/link.ld"
    manifest = build(sources, root/"program.stream",
                     optimization="-O2", stream=True, extra_cflags=flags, extra_libraries=libraries,
                     startup=start, linker_script=linker, compiler=args.compiler)
    (root/"in.bin").write_bytes((root/"program.stream").read_bytes()+incoming)
    frozen = {}
    paths=[source, ROOT/"runtime/gcc/syscalls.c", ROOT/"runtime/gcc/files.c",
                 ROOT/"runtime/gcc/files.h", ROOT/"runtime/copy_c/input_files.h", ROOT/"runtime/rv32i/runtime.c",
                 start, linker]
    if args.fixture=="job": paths.extend([ROOT/"runtime/gcc/job.c", ROOT/"runtime/gcc/job.h"])
    for path in paths:
        destination = root/"sources"/path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
        frozen[str(path.relative_to(ROOT))] = digest(destination)
    print("Built actual RV32I newlib workload; executing primitive Space", flush=True)
    execution = execute_segments(ROOT/"build/bin/space", root/"space", root/"in.bin",
        space_bytes=manifest["space_bytes"], layer_bytes=manifest["layer_bits"]//8,
        ticks=100000, timeout=300, compression="zstd")
    output = (root/"space/program.in").read_bytes()
    assert output == expected.stdout, output
    raw = (root/"space/space.bin").read_bytes()
    def word(at):
        return sum(((raw[(at+i)//8] >> (7-(at+i)%8)) & 1) << i for i in range(32))
    assert raw[:manifest["layer_bits"]//8] == bytes(manifest["layer_bits"]//8)
    assert word(132128) == 10 and word(132160) == 0
    evidence = {"source_sha256": digest(source), "runtime_sources": frozen,
                "newlib_libc_sha256": digest(libc), "newlib_libm_sha256": digest(libm),
                "guest_exit": word(132160), "output_hex": output.hex(),
                "scope": "guest newlib operations only; not GCC execution", **execution}
    (root/"evidence.json").write_text(json.dumps(evidence, indent=2)+"\n")
    print("OK newlib in Space:", args.fixture, "; guest exit 0 and full native output match", flush=True)


if __name__ == "__main__":
    main()
