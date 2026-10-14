"""Compile C main(void) to an RV32I image with IN/OUT and exit support."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "modules"))
from rv32i import Image, Layout, MEMORY_BYTES, SPACE_BYTES
from rv32i_stream import encode_stream
from rv32i_toolchain import Toolchain


def build(sources, output, optimization="-O2", compiler=None, stack=None, stream=False,
          memory_bytes=MEMORY_BYTES, *, extra_cflags=(), extra_libraries=(), report_status=False,
          space_bytes=SPACE_BYTES, startup=None, linker_script=None):
    generator = Image(io=True, memory_bytes=memory_bytes, report_status=report_status,
                      layout=Layout(space_bytes)).build()
    if stack is None:
        stack = memory_bytes-16
    if not 1024 < stack <= memory_bytes or stack % 16:
        raise ValueError(f"stack must be aligned to 16 bytes and within 1040..{memory_bytes}")
    sources = [path.resolve() for path in sources]
    output = output.resolve()
    if output in sources:
        raise ValueError("output must not overwrite a source file")
    tools = Toolchain(compiler)
    artifacts = output.with_name(output.name+".build")
    artifacts.mkdir(parents=True, exist_ok=True)
    runtime = ROOT / "runtime/rv32i"
    startup = Path(startup).resolve() if startup else runtime/"start.S"
    linker_script = Path(linker_script).resolve() if linker_script else runtime/"link.ld"
    elf, binary = artifacts / "program.elf", artifacts / "program.bin"
    command = tools.command(optimization) + [
        "-I", str(runtime), "-T", str(linker_script),
        "-Wl,--defsym=CS_STACK_TOP="+str(stack), "-Wl,-Map="+str(artifacts / "program.map"),
        str(startup), str(runtime / "runtime.c"),
    ] + list(extra_cflags) + [str(path) for path in sources] + list(extra_libraries) + ["-lgcc", "-o", str(elf)]
    (artifacts / "compile.json").write_text(json.dumps(command, indent=2)+"\n")
    result = subprocess.run(command, capture_output=True)
    (artifacts / "compile.stdout").write_bytes(result.stdout)
    (artifacts / "compile.stderr").write_bytes(result.stderr)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors="replace"))
    subprocess.run([tools.objcopy, "-O", "binary", str(elf), str(binary)], check=True)
    assembly = subprocess.run([tools.objdump, "-d", str(elf)], capture_output=True, check=True)
    (artifacts / "disassembly.txt").write_bytes(assembly.stdout)
    image, manifest = generator.encode(binary.read_bytes(), registers={2: stack})
    if stream:
        image, manifest = encode_stream(image, manifest, binary.read_bytes())
    manifest["build_directory"] = str(artifacts)
    manifest["sources"] = [str(path) for path in sources]
    output.write_bytes(image)
    output.with_name(output.name+".json").write_text(json.dumps(manifest, indent=2)+"\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--optimization", choices=["O0", "O1", "O2", "O3", "Os"], default="O2")
    parser.add_argument("--compiler")
    parser.add_argument("--stream", action="store_true", help="produce a checked IN stream instead of a core image")
    parser.add_argument("--report-status", action="store_true", help="emit a terminal OUT record inside space")
    parser.add_argument("--stack", type=lambda text: int(text, 0))
    parser.add_argument("--memory-bytes", type=lambda text: int(text, 0), default=MEMORY_BYTES)
    parser.add_argument("--space-bytes", type=lambda text: int(text, 0), default=SPACE_BYTES)
    args = parser.parse_args()
    try:
        build(args.sources, args.output, "-"+args.optimization, args.compiler, args.stack,
              args.stream, args.memory_bytes, report_status=args.report_status,
              space_bytes=args.space_bytes)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error)+"\n")


if __name__ == "__main__":
    main()
