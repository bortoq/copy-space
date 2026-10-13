"""Build the Forth compiler image; never parse or compile the user's C here."""
import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/pforth"))
from common import PORT, sources, flags
from prepare import prepare
sys.path.insert(0, str(ROOT / "scripts/rv32i"))
from build import build as build_rv32i

FORTH = ROOT / "runtime/copy_c/compiler.fth"


def build(output, compiler=None, prepare_only=False, *, space_bytes=67108864,
          memory_bytes=16777216):
    output = output.resolve()
    if output == FORTH.resolve():
        raise ValueError("output must not overwrite the Forth compiler source")
    output.parent.mkdir(parents=True, exist_ok=True)
    artifacts = output.with_name(output.name+".build")
    dictionary = artifacts / "dictionary/pfdicdat.h"
    signature = hashlib.sha256(FORTH.read_bytes()).hexdigest()
    custom_signature = hashlib.sha256((PORT / "custom.c").read_bytes()).hexdigest()
    fold_signature = hashlib.sha256((FORTH.parent / "integer64_fold.h").read_bytes()).hexdigest()
    phase2_signature = hashlib.sha256((FORTH.parent / "preprocess_phase2.h").read_bytes()).hexdigest()
    macros_signature = hashlib.sha256((FORTH.parent / "preprocess_macros.h").read_bytes()).hexdigest()
    metadata = dictionary.with_name(dictionary.name+".json")
    cached = json.loads(metadata.read_text()) if metadata.is_file() else {}
    if (cached.get("compiler_forth_sha256") != signature
            or cached.get("compiler_custom_sha256") != custom_signature
            or cached.get("compiler_integer64_fold_sha256") != fold_signature
            or cached.get("compiler_preprocess_phase2_sha256") != phase2_signature
            or cached.get("compiler_preprocess_macros_sha256") != macros_signature
            or cached.get("headers_reserve_bytes") != 4096
            or cached.get("code_reserve_bytes") != 8192
            or cached.get("prepare_code_capacity_bytes") != 4194304
            or cached.get("prepare_pool_bytes") != 8388608):
        prepare_flags = ["-DCOPY_SPACE_C_COMPILER", "-UPF_DEFAULT_HEADER_SIZE",
                         "-DPF_DEFAULT_HEADER_SIZE=65536", "-UPF_DEFAULT_CODE_SIZE",
                         "-DPF_DEFAULT_CODE_SIZE=4194304", "-UPF_MEM_POOL_SIZE",
                         "-DPF_MEM_POOL_SIZE=8388608"]
        manifest = prepare(dictionary, [FORTH], prepare_flags, artifacts / "prepare",
                           headers_reserve=4096, code_reserve=8192)
        manifest["compiler_forth_sha256"] = signature
        manifest["compiler_custom_sha256"] = custom_signature
        manifest["compiler_integer64_fold_sha256"] = fold_signature
        manifest["compiler_preprocess_phase2_sha256"] = phase2_signature
        manifest["compiler_preprocess_macros_sha256"] = macros_signature
        manifest["prepare_code_capacity_bytes"] = 4194304
        manifest["prepare_pool_bytes"] = 8388608
        metadata.write_text(json.dumps(manifest, indent=2)+"\n")
    manifest = json.loads(metadata.read_text())
    if hashlib.sha256(dictionary.read_bytes()).hexdigest() != manifest["header_sha256"]:
        raise ValueError("compiler dictionary checksum mismatch")
    port_flags = ["-I"+str(dictionary.parent), "-DCOPY_SPACE_C_COMPILER"] + flags()
    port_flags += ["-UPF_MEM_POOL_SIZE", "-DPF_MEM_POOL_SIZE=8388608"]
    native = artifacts / "compiler32"
    command = shlex.split(os.environ.get("CC", "cc")) + [
        "-m32", "-O2", "-g", "-std=c99", "-ffreestanding", "-nostdlib", "-fno-pie", "-no-pie",
        "-fno-stack-protector", "-Wl,--build-id=none", "-Wl,-e,_start",
    ] + port_flags + [str(path) for path in sources()] + [
        str(PORT / "bootstrap/linux32.c"), "-o", str(native)]
    (artifacts / "native-compile.json").write_text(json.dumps(command, indent=2)+"\n")
    result = subprocess.run(command, capture_output=True)
    (artifacts / "native-compile.stderr").write_bytes(result.stderr)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors="replace"))
    if not prepare_only:
        image = build_rv32i(sources(), output, compiler=compiler, stream=True,
                           extra_cflags=port_flags, space_bytes=space_bytes,
                           memory_bytes=memory_bytes)
        image.update({"compiler_forth_sha256": signature, "compiler_dictionary": manifest})
        output.with_name(output.name+".json").write_text(json.dumps(image, indent=2)+"\n")
    return native


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=ROOT / "build/copy-c/compiler.stream")
    parser.add_argument("--compiler")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--space-bytes", type=lambda text: int(text, 0), default=67108864)
    parser.add_argument("--memory-bytes", type=lambda text: int(text, 0), default=16777216)
    args = parser.parse_args()
    try:
        native = build(args.output, args.compiler, args.prepare_only,
                       space_bytes=args.space_bytes, memory_bytes=args.memory_bytes)
        print(f"copy-c: {native if args.prepare_only else args.output}")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, str(error)+"\n")


if __name__ == "__main__":
    main()
