"""Compare guest memory operations with the pinned byte implementation."""
import argparse
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/pforth"))
from common import PORT, UPSTREAM, flags
sys.path.insert(0, str(ROOT / "scripts/rv32i"))
from build import build
from space_segments import execute_segments


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path,
                        default=ROOT / "tmp/space-tests/pforth-word-memory-final")
    args = parser.parse_args()
    folder = args.root.resolve()
    folder.mkdir(parents=True, exist_ok=False)
    fixture = ROOT / "tests/fixtures/pforth/memory.c"
    library = PORT / "clib.c"
    source_hashes = {str(path.relative_to(ROOT)): sha(path)
                     for path in (fixture, library, UPSTREAM / "csrc/pf_clib.c")}
    native = folder / "native32"
    command = ["gcc", "-m32", "-O2", "-std=c99", "-ffreestanding",
               "-nostdlib", "-fno-pie", "-no-pie", "-fno-stack-protector",
               "-Wl,--build-id=none", "-Wl,-e,_start"] + flags() + [
                   str(fixture), str(library), str(PORT / "bootstrap/linux32.c"),
                   "-o", str(native)]
    (folder / "native-args.json").write_text(json.dumps(command, indent=2)+"\n")
    compiled = subprocess.run(command, capture_output=True, timeout=60)
    (folder / "native-compile.stdout").write_bytes(compiled.stdout)
    (folder / "native-compile.stderr").write_bytes(compiled.stderr)
    assert compiled.returncode == 0, compiled.stderr
    result = subprocess.run([str(native)], capture_output=True, timeout=30)
    (folder / "native.out").write_bytes(result.stdout)
    (folder / "native.stderr").write_bytes(result.stderr)
    assert result.returncode == 0 and result.stderr == b"", result
    assert result.stdout == struct.pack("<II", 7, 26401), result.stdout
    print("OK pForth memory: 26401 native checks", flush=True)

    incoming = folder / "empty.in"
    incoming.write_bytes(b"")
    proofs = {}
    for name in ("baseline", "word"):
        core = folder / (name+".core")
        options = flags()+["-DMEMORY_GUEST"]
        if name == "baseline":
            options.append("-DMEMORY_BASELINE")
        manifest = build([fixture, library], core, extra_cflags=options,
                         memory_bytes=65536, space_bytes=2097152)
        execution = folder / name
        proof = execute_segments(ROOT / "build/bin/space", execution, incoming,
                                 space_bytes=2097152, layer_bytes=2272,
                                 ticks=500000, timeout=900, initial_core=core)
        output = (execution / "program.in").read_bytes()
        assert output == struct.pack("<II", 7, 150), (name, output)
        raw = (execution / "space.bin").read_bytes()
        address = manifest["exit_code_bit"]
        exit_code = sum(((raw[(address+i)//8] >> (7-(address+i)%8)) & 1) << i
                        for i in range(32))
        assert exit_code == 0, (name, exit_code)
        proof.update({"exit_code": exit_code, "checks": 150,
                      "core_sha256": sha(core), "output_sha256": sha(execution / "program.in")})
        proofs[name] = proof
        (execution / "proof.json").write_text(json.dumps(proof, indent=2)+"\n")
        print(f"OK pForth memory {name}: {proof['copy_events']} copies", flush=True)
    assert proofs["word"]["copy_events"] < proofs["baseline"]["copy_events"], proofs
    summary = {"sources": source_hashes, "native_checks": 26401,
               "native_sha256": sha(native), "space": proofs,
               "copy_ratio": proofs["word"]["copy_events"] / proofs["baseline"]["copy_events"]}
    (folder / "summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(f"OK memory equivalence and copy reduction: {summary['copy_ratio']:.3f}", flush=True)


if __name__ == "__main__":
    main()
