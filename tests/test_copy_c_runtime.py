"""Check a runtime rebuild against complete packets from a proved compiler run.

This is a host reference check. It does not replace compiler execution in
space. Byte-identical packets retain the previous direct-target evidence.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--compiler", type=Path,
                        default=ROOT / "build/copy-c/compiler.stream.build/compiler32")
    args = parser.parse_args()
    baseline = args.baseline.resolve()
    compiler = args.compiler.resolve()
    summary = json.loads((baseline / "native-summary.json").read_text())
    source = ROOT / "runtime/copy_c/compiler.fth"
    assert sha(source) == sha(baseline / "compiler.fth") == summary["compiler_forth_sha256"]
    folder = args.artifacts.resolve()
    folder.mkdir(parents=True, exist_ok=False)
    cases = []
    for incoming in sorted((baseline / "native").glob("*/in.bin")):
        packet = incoming.with_name("program.in")
        errors = incoming.with_name("stderr.txt")
        assert packet.is_file() and errors.is_file(), incoming
        expected = packet.read_bytes()
        code = 2 if expected.startswith(b"copy-c error at byte ") else 0
        result = subprocess.run([str(compiler)], input=incoming.read_bytes(),
                                capture_output=True, timeout=30)
        assert (result.returncode, result.stdout, result.stderr) == (
            code, expected, errors.read_bytes()), incoming.parent.name
        if code == 0:
            target_input = baseline / "target" / incoming.parent.name / "in.bin"
            assert target_input.is_file() and sha(target_input) == sha(packet)
        cases.append({"name": incoming.parent.name, "exit_code": code,
                      "input_sha256": sha(incoming), "packet_sha256": sha(packet),
                      "stderr_sha256": sha(errors), "packet_bytes": len(expected)})
    rejected = sum(case["exit_code"] == 2 for case in cases)
    assert rejected == summary["rejected"]
    guard_cases = len(cases)-rejected-summary["valid"]-summary["arithmetic_faults"]
    assert guard_cases >= 0
    proof = {"execution": "host packet equivalence; targets proved by baseline",
             "baseline": str(baseline), "baseline_summary_sha256": sha(baseline / "native-summary.json"),
             "baseline_native_sha256": summary["native_compiler_sha256"],
             "native_sha256": sha(compiler), "compiler_forth_sha256": sha(source),
             "guard_cases": guard_cases,
             "runtime_sources": {str(path.relative_to(ROOT)): sha(path) for path in (
                 ROOT / "runtime/pforth/clib.c", ROOT / "scripts/pforth/common.py")},
             "cases": cases}
    (folder / "proof.json").write_text(json.dumps(proof, indent=2)+"\n")
    print(f"OK compiler runtime: {len(cases)} complete packets, {rejected} rejections", flush=True)


if __name__ == "__main__":
    main()
