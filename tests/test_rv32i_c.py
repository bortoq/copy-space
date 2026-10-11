"""Compile actual C into RV32I and execute the binary through space copies."""
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "modules"))
from rv32i import Image
from rv32i_reference import execute

root = Path("tmp/space-tests/rv32i-c")
root.mkdir(parents=True, exist_ok=True)
fixture = Path("tests/fixtures/rv32i")
local = Path("tmp/rv32i-toolchain/root/usr/bin/riscv64-unknown-elf-gcc")
compiler = os.environ.get("RISCV_CC") or shutil.which("riscv64-unknown-elf-gcc")
if not compiler and local.is_file():
    compiler = str(local.resolve())
if not compiler:
    sys.exit("RISC-V GCC not found; set RISCV_CC to a compiler supporting -march=rv32i -mabi=ilp32")
compiler = str(Path(compiler).resolve()) if Path(compiler).is_file() else compiler
prefix = compiler[:-3] if compiler.endswith("gcc") else "riscv64-unknown-elf-"
objcopy = os.environ.get("RISCV_OBJCOPY", prefix+"objcopy")
objdump = os.environ.get("RISCV_OBJDUMP", prefix+"objdump")
tool_directory = Path(compiler).parent.parent / "lib" / "riscv64-unknown-elf" / "bin"
tool_flags = ["-B" + str(tool_directory) + "/"] if (tool_directory / "as").is_file() else []

native_source = root / "native.c"
native_source.write_text('#include <stdio.h>\nextern unsigned int rv_example(void);\n'
                         'int main(void) { printf("%08x\\n", rv_example()); return 0; }\n')
subprocess.run(shlex.split(os.environ.get("CC", "cc")) + ["-O2", str(fixture / "add_sum.c"),
               str(native_source), "-o", str(root / "native")], check=True)
native = subprocess.run([str(root / "native")], capture_output=True, check=True).stdout
(root / "native.out").write_bytes(native)
expected_c = int(native, 16)

for optimization in ["-O0", "-O2"]:
    folder = root / optimization[1:]
    folder.mkdir(exist_ok=True)
    elf, binary = folder / "program.elf", folder / "program.bin"
    command = [compiler] + tool_flags + [optimization, "-march=rv32i", "-mabi=ilp32", "-mno-relax",
               "-msmall-data-limit=0", "-ffreestanding", "-fno-pic", "-fno-stack-protector",
               "-nostdlib", "-nostartfiles", "-Wall", "-Wextra", "-Werror",
               "-Wl,--build-id=none", "-T", str(fixture / "link.ld"),
               str(fixture / "start.S"), str(fixture / "add_sum.c"), "-o", str(elf)]
    (folder / "compile.json").write_text(json.dumps(command, indent=2)+"\n")
    result = subprocess.run(command, capture_output=True)
    (folder / "compile.stderr").write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr.decode()
    subprocess.run([objcopy, "-O", "binary", str(elf), str(binary)], check=True)
    dump = subprocess.run([objdump, "-d", str(elf)], capture_output=True, check=True).stdout
    (folder / "disassembly.txt").write_bytes(dump)
    program = binary.read_bytes()
    expected, memory, _ = execute(program, max_steps=20000)
    assert expected[-1][-1] == 1 and expected[-1][10] == expected_c
    image, manifest = Image(True, memory_bytes=65536).build().encode(program)
    (folder / "core.bin").write_bytes(image)
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    (folder / "in.bin").write_bytes(b"")
    args = ["build/bin/space_image_proof", "--core", str(folder / "core.bin"),
            "--in", str(folder / "in.bin"), "--out", str(folder / "out.bin"),
            "--dump-space", str(folder / "space.bin"), "--trace", str(folder / "trace.txt"),
            "--report", str(folder / "report.txt"), "--ticks", str(100*len(expected)+100)]
    (folder / "args.json").write_text(json.dumps(args, indent=2)+"\n")
    result = subprocess.run(args, capture_output=True, timeout=30)
    (folder / "stderr.txt").write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr
    out = (folder / "out.bin").read_bytes()
    assert len(out) == 136*len(expected)
    frames = []
    for offset in range(0, len(out), 136):
        frame = out[offset:offset+136]
        frames.append([sum(((frame[j*4+i//8] >> (7-i%8)) & 1) << i for i in range(32))
                       for j in range(34)])
    assert frames == expected
    (folder / "states.json").write_text(json.dumps(frames, indent=2)+"\n")
    raw = (folder / "space.bin").read_bytes()
    assert raw[8388608//8:8388608//8+65536] == memory
    assert raw[:2272] == bytes(2272)
    report = dict(line.split("=", 1) for line in (folder / "report.txt").read_text().splitlines())
    assert report["stop"] == "idle"
    # Ordinary production executable must produce the same complete state stream.
    actual = subprocess.run(["build/bin/space", "--core", str(folder / "core.bin")],
                            input=b"", capture_output=True, check=True, timeout=30)
    (folder / "space.out").write_bytes(actual.stdout)
    assert actual.stdout == out
    print(f"OK C {optimization}: {len(program)} bytes, {len(frames)} states, "
          f"{report['ticks']} ticks, a0=0x{frames[-1][10]:08x}")
