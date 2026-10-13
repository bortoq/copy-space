"""Prove the compiler's 64-bit arithmetic procedures by direct space execution.

This tests the emitted arithmetic, not the C frontend or the function ABI.
Every complete eight-byte result is checked against Python and GNU C.
"""
import argparse
import hashlib
import json
import random
import subprocess
from pathlib import Path

from space_archive import archive_target

ROOT = Path(__file__).resolve().parents[1]
MASK = (1 << 64)-1
OPS = ("add", "sub", "eq", "lt", "ult", "and", "or", "xor", "not",
       "shl", "shr", "sar", "mul", "div", "udiv", "mod", "umod", "bool", "chain")


def signed(n):
    return n-(1 << 64) if n >> 63 else n


def result(op, a, b):
    sa, sb = signed(a), signed(b)
    if op in ("div", "mod"):
        q = (abs(sa)//abs(sb)) * (-1 if (sa < 0) != (sb < 0) else 1)
        return (q if op == "div" else sa-q*sb) & MASK
    return {
        "add": lambda: a+b, "sub": lambda: a-b,
        "eq": lambda: int(a == b), "lt": lambda: int(sa < sb),
        "ult": lambda: int(a < b), "and": lambda: a & b,
        "or": lambda: a | b, "xor": lambda: a ^ b,
        "not": lambda: ~a, "shl": lambda: a << b,
        "shr": lambda: a >> b, "sar": lambda: sa >> b,
        "mul": lambda: a*b, "udiv": lambda: a//b,
        "umod": lambda: a % b, "bool": lambda: int(a != 0),
        "chain": lambda: (((((a+b) & MASK) ^ b)*b) & MASK)//b,
    }[op]() & MASK


def cases():
    pairs = [(0, 0), (0, 1), (1, 0), (1, 1), (MASK, 1), (1, MASK),
             (MASK, MASK), (1 << 32, 1), ((1 << 32)-1, 1),
             (1 << 63, 3), ((1 << 63)-1, 1 << 63), (1 << 63, (1 << 63)+1),
             (1 << 63, (1 << 63)-1), (0x123456789abcdef0, 0xfedcba9876543210)]
    rng = random.Random(0xC064)
    pairs += [(rng.getrandbits(64), rng.getrandbits(64) or 1) for _ in range(12)]
    good = []
    for op in OPS:
        inputs = pairs
        if op in ("shl", "shr", "sar"):
            inputs = [(a, n) for a in (0, 1, MASK, 1 << 63, 0x123456789abcdef0)
                      for n in (0, 1, 31, 32, 33, 62, 63)]
        for i, (a, b) in enumerate(inputs):
            if op in ("div", "mod", "udiv", "umod", "chain") and b == 0:
                continue
            if op in ("div", "mod") and a == 1 << 63 and b == MASK:
                continue
            good.append((f"{op}-{i}", op, a, b, result(op, a, b)))
    for bit in range(64):
        for op, a, b in (("add", (1 << bit)-1, 1), ("sub", 1 << bit, 1),
                         ("bool", 1 << bit, 0), ("eq", 1 << bit, 1 << bit)):
            good.append((f"{op}-bit-{bit}", op, a, b, result(op, a, b)))
    faults = [(f"{op}-zero", op, MASK, 0, b"copy-c: divide by zero\n")
              for op in ("div", "udiv", "mod", "umod")]
    faults += [(f"{op}-bad-{i}", op, 1 << 63, b, b"copy-c: shift error\n")
               for op in ("shl", "shr", "sar")
               for i, b in enumerate((64, 65, MASK, 1 << 32, 1 << 63))]
    return good, faults


def program(op, a, b):
    # Immutable operands are outside the runtime scratch fields and the C frame.
    lines = ["decimal", ": INTEGER64-PROOF",
             "0 cc-unevaluated ! cc-code-base cc-origin !",
             "cc-image-base cc-emission-base ! cc-image cc-emission-buffer !"]
    for at, value in ((202240, a), (202304, b)):
        lines += [f"{value & 0xffffffff} 32 {at} cc-value!",
                  f"{value >> 32} 32 {at+32} cc-value!"]
    lines += ["cc-boundary 32 64 cc-guard-constants cc-bits!"]
    for i, step in enumerate(("add", "xor", "mul", "udiv") if op == "chain" else (op,)):
        lines += [f"64 cc-wide-a {'202240' if i == 0 else 'cc-wide-r'} cc-op",
                  "64 cc-wide-b 202304 cc-op",
                  f"cc-wide-{step}-entry @ cc-library-call"]
    lines += ["cc-wide-output-entry @ cc-jump",
              "cc-current cc-image-base - 2 * 32 0 cc-guard-constants cc-bits!",
              "cc-export 0 cs-exit ;", "INTEGER64-PROOF", ""]
    return "\n".join(lines).encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--probe", action="store_true", help="one case for each procedure and all faults")
    args = parser.parse_args()
    folder = args.artifacts.resolve()
    folder.mkdir(parents=True, exist_ok=False)
    compiler = ROOT / "build/copy-c/compiler.stream.build/compiler32"
    forth = ROOT / "runtime/copy_c/compiler.fth"
    fixture = ROOT / "tests/fixtures/copy_c/integer64_reference.c"
    for name, path in (("compiler.fth", forth), ("compiler32", compiler),
                       ("integer64_reference.c", fixture)):
        (folder / name).write_bytes(path.read_bytes())
    compiler = folder / "compiler32"
    compiler.chmod(0o755)
    good, faults = cases()
    if args.probe:
        good = [next(c for c in good if c[1] == op and c[2] >> 32 and c[3] != 0
                     and (op != "chain" or c[0] == "chain-7")) for op in OPS]
    gcc = ["gcc", "-std=gnu11", "-O0", "-Wall", "-Wextra", "-Werror", str(fixture),
           "-o", str(folder / "reference")]
    (folder / "gcc-args.json").write_text(json.dumps(gcc, indent=2)+"\n")
    built = subprocess.run(gcc, capture_output=True, timeout=30)
    (folder / "gcc.stdout").write_bytes(built.stdout)
    (folder / "gcc.stderr").write_bytes(built.stderr)
    assert built.returncode == 0, built.stderr
    incoming = "".join(f"{OPS.index(op)} {a:x} {b:x}\n" for _, op, a, b, _ in good).encode()
    (folder / "reference.in").write_bytes(incoming)
    reference = subprocess.run([str(folder / "reference")], input=incoming,
                               capture_output=True, timeout=30)
    (folder / "reference.out").write_bytes(reference.stdout)
    (folder / "reference.stderr").write_bytes(reference.stderr)
    assert reference.returncode == 0 and reference.stderr == b""
    assert [int(s, 16) for s in reference.stdout.splitlines()] == [c[4] for c in good]
    evidence = []
    for name, op, a, b, expected in good+faults:
        target = folder / "target" / name
        target.mkdir(parents=True)
        source = program(op, a, b)
        (target / "source.fth").write_bytes(source)
        (target / "compile-args.json").write_text(json.dumps([str(compiler)])+"\n")
        compiled = subprocess.run([str(compiler)], input=source, capture_output=True, timeout=30)
        (target / "compile.out").write_bytes(compiled.stdout)
        (target / "compile.stderr").write_bytes(compiled.stderr)
        assert compiled.returncode == 0 and compiled.stderr == b"", (name, compiled)
        (target / "in.bin").write_bytes(compiled.stdout)
        command = [str(ROOT / "build/bin/space"), "--ticks", "20000", "--trace", str(target / "trace.txt"),
                   "--dump-space", str(target / "space.bin")]
        (target / "args.json").write_text(json.dumps(command, indent=2)+"\n")
        executed = subprocess.run(command, input=compiled.stdout, capture_output=True, timeout=30)
        (target / "result.out").write_bytes(executed.stdout)
        (target / "stderr.txt").write_bytes(executed.stderr)
        want = expected if isinstance(expected, bytes) else expected.to_bytes(8, "little")
        assert executed.returncode == 0 and executed.stderr == b"", (name, executed)
        assert executed.stdout == want, (name, executed.stdout.hex(), want.hex())
        raw = (target / "space.bin").read_bytes()
        assert len(raw) == 2097152 and raw[:2272] == bytes(2272)
        trace = (target / "trace.txt").read_bytes()
        assert trace.splitlines()[-1].endswith(b" idle")
        record = {"name": name, "operation": op, "a": hex(a), "b": hex(b),
                  "output": want.hex(), "packet_sha256": hashlib.sha256(compiled.stdout).hexdigest(),
                  "copy_events": sum(row.startswith(b"copy ") for row in trace.splitlines()),
                  "trace_sha256": hashlib.sha256(trace).hexdigest()}
        (target / "evidence.json").write_text(json.dumps(record, indent=2)+"\n")
        archive_target(target)
        evidence.append(record)
        print(f"OK integer64 {name}: {record['copy_events']} copies, OUT={want.hex()}", flush=True)
    proof = {"scope": "direct arithmetic procedures; not C frontend or call ABI",
             "valid": len(good), "faults": len(faults), "gcc_compared": len(good),
             "sources": {name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
                         for name in ("compiler.fth", "compiler32", "integer64_reference.c")},
             "cases": evidence}
    (folder / "summary.json").write_text(json.dumps(proof, indent=2)+"\n")
    print(f"OK integer64: {len(good)} full results, {len(faults)} faults", flush=True)


if __name__ == "__main__":
    main()
