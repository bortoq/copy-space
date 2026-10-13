"""Compile a saved C case in space and run its direct-copy result.

Use a complete previously proved packet as the reference without replaying
the whole native test suite. All production parsing remains inside space.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from space_segments import execute_segments

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--case", required=True)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    assert Path(args.case).name == args.case
    baseline = args.baseline.resolve()
    folder = args.artifacts.resolve()
    incoming = (baseline / "native" / args.case / "in.bin").read_bytes()
    assert incoming.startswith(b"CC-RUN\n")
    source = incoming[len(b"CC-RUN\n"):]
    reference = (baseline / "native" / args.case / "program.in").read_bytes()
    target_reference = baseline / "target" / args.case
    assert reference == (target_reference / "in.bin").read_bytes()
    expected = (target_reference / "result.out").read_bytes()
    image_path = ROOT / "build/copy-c/compiler.stream"
    if not args.resume:
        folder.mkdir(parents=True, exist_ok=False)
        image = image_path.read_bytes()
        manifest = json.loads(image_path.with_name(image_path.name+".json").read_text())
        forth = (ROOT / "runtime/copy_c/compiler.fth").read_bytes()
        assert sha(forth) == manifest["compiler_forth_sha256"]
        assert forth == (baseline / "compiler.fth").read_bytes()
        assert source not in (image_path.with_name(image_path.name+".build") / "program.bin").read_bytes()
        (folder / "compiler.json").write_text(json.dumps(manifest, indent=2)+"\n")
        for name, content in (("compiler.fth", forth), ("source.c", source),
                              ("in.bin", image+incoming), ("reference.in", reference),
                              ("expected.out", expected)):
            (folder / name).write_bytes(content)
        for name in ("custom.c", "clib.c"):
            (folder / name).write_bytes((ROOT / "runtime/pforth" / name).read_bytes())
        if "compiler_integer64_fold_sha256" in manifest["compiler_dictionary"]:
            fold = (ROOT / "runtime/copy_c/integer64_fold.h").read_bytes()
            assert sha(fold) == manifest["compiler_dictionary"]["compiler_integer64_fold_sha256"]
            (folder / "integer64_fold.h").write_bytes(fold)
        if "compiler_preprocess_phase2_sha256" in manifest["compiler_dictionary"]:
            phase2 = (ROOT / "runtime/copy_c/preprocess_phase2.h").read_bytes()
            assert sha(phase2) == manifest["compiler_dictionary"]["compiler_preprocess_phase2_sha256"]
            (folder / "preprocess_phase2.h").write_bytes(phase2)
        if "compiler_preprocess_macros_sha256" in manifest["compiler_dictionary"]:
            macros = (ROOT / "runtime/copy_c/preprocess_macros.h").read_bytes()
            assert sha(macros) == manifest["compiler_dictionary"]["compiler_preprocess_macros_sha256"]
            (folder / "preprocess_macros.h").write_bytes(macros)
        if "compiler_preprocess_condition_sha256" in manifest["compiler_dictionary"]:
            condition = (ROOT / "runtime/copy_c/preprocess_condition.h").read_bytes()
            assert sha(condition) == manifest["compiler_dictionary"]["compiler_preprocess_condition_sha256"]
            (folder / "preprocess_condition.h").write_bytes(condition)
        for name in ("input_files", "preprocess_include", "preprocess_queries"):
            key="compiler_"+name+"_sha256"
            if key in manifest["compiler_dictionary"]:
                content=(ROOT / "runtime/copy_c" / (name+".h")).read_bytes()
                assert sha(content)==manifest["compiler_dictionary"][key]
                (folder / (name+".h")).write_bytes(content)
    else:
        manifest = json.loads((folder / "compiler.json").read_text())
        assert (folder / "source.c").read_bytes() == source
        assert (folder / "reference.in").read_bytes() == reference
        assert (folder / "expected.out").read_bytes() == expected
    image = (folder / "in.bin").read_bytes()[:manifest["stream_bytes"]]
    assert (folder / "in.bin").read_bytes() == image+incoming
    assert sha((folder / "compiler.fth").read_bytes()) == manifest["compiler_forth_sha256"]
    runtime_names = ("custom.c", "clib.c")
    if "compiler_integer64_fold_sha256" in manifest["compiler_dictionary"]:
        assert sha((folder / "integer64_fold.h").read_bytes()) == manifest["compiler_dictionary"]["compiler_integer64_fold_sha256"]
        runtime_names += ("integer64_fold.h",)
    if "compiler_preprocess_phase2_sha256" in manifest["compiler_dictionary"]:
        assert sha((folder / "preprocess_phase2.h").read_bytes()) == manifest["compiler_dictionary"]["compiler_preprocess_phase2_sha256"]
        runtime_names += ("preprocess_phase2.h",)
    if "compiler_preprocess_macros_sha256" in manifest["compiler_dictionary"]:
        assert sha((folder / "preprocess_macros.h").read_bytes()) == manifest["compiler_dictionary"]["compiler_preprocess_macros_sha256"]
        runtime_names += ("preprocess_macros.h",)
    if "compiler_preprocess_condition_sha256" in manifest["compiler_dictionary"]:
        assert sha((folder / "preprocess_condition.h").read_bytes()) == manifest["compiler_dictionary"]["compiler_preprocess_condition_sha256"]
        runtime_names += ("preprocess_condition.h",)
    for name in ("input_files", "preprocess_include", "preprocess_queries"):
        key="compiler_"+name+"_sha256"
        if key in manifest["compiler_dictionary"]:
            assert sha((folder / (name+".h")).read_bytes())==manifest["compiler_dictionary"][key]
            runtime_names += (name+".h",)
    emulator = {2097152: ROOT / "build/bin/space", 67108864: ROOT / "build/bin/space-64m"}[manifest["space_bytes"]]
    proof = execute_segments(emulator, folder, folder / "in.bin",
                             space_bytes=manifest["space_bytes"],
                             layer_bytes=manifest["layer_bits"]//8,
                             ticks=500000, timeout=900, resume=args.resume)
    output = (folder / "program.in").read_bytes()
    assert output == reference
    raw = (folder / "space.bin").read_bytes()
    def word(at):
        return sum(((raw[(at+i)//8] >> (7-(at+i)%8)) & 1) << i for i in range(32))
    assert word(manifest["status_bit"]) == 10 and word(manifest["exit_code_bit"]) == 0
    target = folder / "target"
    target.mkdir()
    command = [str(ROOT / "build/bin/space"), "--ticks", "20000", "--trace", str(target / "trace.txt"),
               "--dump-space", str(target / "space.bin")]
    (target / "args.json").write_text(json.dumps(command, indent=2)+"\n")
    (target / "in.bin").write_bytes(output)
    result = subprocess.run(command, input=output, capture_output=True, timeout=30)
    (target / "result.out").write_bytes(result.stdout)
    (target / "stderr.txt").write_bytes(result.stderr)
    assert result.returncode == 0 and result.stderr == b"" and result.stdout == expected
    assert (target / "trace.txt").read_bytes().splitlines()[-1].endswith(b" idle")
    assert (target / "space.bin").read_bytes()[:2272] == bytes(2272)
    proof.update({"case": args.case, "guest_exit": 0, "source_sha256": sha(source),
                  "output_sha256": sha(output), "compiler_image_sha256": sha(image),
                  "compiler_forth_sha256": manifest["compiler_forth_sha256"],
                  "runtime_sources": {name: sha((folder / name).read_bytes())
                                      for name in runtime_names}})
    (folder / "evidence.json").write_text(json.dumps(proof, indent=2)+"\n")
    print(f"OK C compiled in space and executed directly: {args.case}, OUT={result.stdout.hex()}", flush=True)


if __name__ == "__main__":
    main()
