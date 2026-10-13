"""Generate a proved integer64 procedure call inside space, then execute it.

The input is a Forth emission fixture, not a long long C program. This proves
the new library is usable from the compiler dictionary inside space.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from space_archive import archive_target
from space_segments import execute_segments

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--case", default="chain-7")
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    assert Path(args.case).name == args.case
    baseline, folder = args.baseline.resolve(), args.artifacts.resolve()
    source = baseline / "target" / args.case
    reference = (source / "in.bin").read_bytes()
    expected = (source / "result.out").read_bytes()
    emission = (source / "source.fth").read_bytes()
    summary = json.loads((baseline / "summary.json").read_text())
    assert len(expected) == 8 and any(c["name"] == args.case for c in summary["cases"])
    image_path = ROOT / "build/copy-c/compiler.stream"
    if not args.resume:
        folder.mkdir(parents=True, exist_ok=False)
        image = image_path.read_bytes()
        manifest = json.loads(image_path.with_name(image_path.name+".json").read_text())
        forth = (ROOT / "runtime/copy_c/compiler.fth").read_bytes()
        assert sha(forth) == manifest["compiler_forth_sha256"] == summary["sources"]["compiler.fth"]
        assert emission not in (image_path.with_name(image_path.name+".build") / "program.bin").read_bytes()
        for name, data in (("compiler.fth", forth), ("source.fth", emission),
                           ("reference.in", reference), ("expected.out", expected), ("in.bin", image+emission)):
            (folder / name).write_bytes(data)
        for name in ("custom.c", "clib.c"):
            (folder / name).write_bytes((ROOT / "runtime/pforth" / name).read_bytes())
        (folder / "compiler.json").write_text(json.dumps(manifest, indent=2)+"\n")
    else:
        manifest = json.loads((folder / "compiler.json").read_text())
        assert (folder / "source.fth").read_bytes() == emission
        assert (folder / "reference.in").read_bytes() == reference
        assert (folder / "expected.out").read_bytes() == expected
    incoming = (folder / "in.bin").read_bytes()
    image = incoming[:manifest["stream_bytes"]]
    assert incoming == image+emission
    assert sha((folder / "compiler.fth").read_bytes()) == manifest["compiler_forth_sha256"]
    proof = execute_segments(ROOT / "build/bin/space-64m", folder, folder / "in.bin",
                             space_bytes=manifest["space_bytes"], layer_bytes=manifest["layer_bits"]//8,
                             ticks=500000, timeout=900, resume=args.resume)
    output = (folder / "program.in").read_bytes()
    assert output == reference
    raw = (folder / "space.bin").read_bytes()
    word = lambda at: sum(((raw[(at+i)//8] >> (7-(at+i)%8)) & 1) << i for i in range(32))
    assert word(manifest["status_bit"]) == 10 and word(manifest["exit_code_bit"]) == 0
    target = folder / "target"
    target.mkdir()
    command = [str(ROOT / "build/bin/space"), "--ticks", "20000", "--trace", str(target / "trace.txt"),
               "--dump-space", str(target / "space.bin")]
    (target / "args.json").write_text(json.dumps(command, indent=2)+"\n")
    (target / "in.bin").write_bytes(output)
    ran = subprocess.run(command, input=output, capture_output=True, timeout=30)
    (target / "result.out").write_bytes(ran.stdout)
    (target / "stderr.txt").write_bytes(ran.stderr)
    assert ran.returncode == 0 and ran.stderr == b"" and ran.stdout == expected
    assert (target / "space.bin").read_bytes()[:2272] == bytes(2272)
    archive_target(target)
    proof.update({"scope": "Forth emission and direct integer64 execution; not C frontend",
                  "case": args.case, "guest_exit": 0, "source_sha256": sha(emission),
                  "packet_sha256": sha(output), "output": expected.hex(),
                  "compiler_image_sha256": sha(image), "compiler_forth_sha256": manifest["compiler_forth_sha256"]})
    (folder / "evidence.json").write_text(json.dumps(proof, indent=2)+"\n")
    print(f"OK integer64 emitted inside space: {args.case}, OUT={ran.stdout.hex()}", flush=True)


if __name__ == "__main__":
    main()
