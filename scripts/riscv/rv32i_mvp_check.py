#!/usr/bin/env python3
"""RV32I MVP checker for C2 trace->f0 stage.

This is a phase-0/phase-2 harness: it validates tracer outputs and emits
artifacts for debugging. It does not claim full VM-level equivalence yet.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def run(cmd):
    p = subprocess.run(cmd, text=True, capture_output=True)
    return p.returncode, p.stdout, p.stderr


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def trace_digest(trace):
    h = hashlib.sha256()
    for e in trace:
        h.update(json.dumps(e, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description="Check RV32I MVP trace->f0 artifacts")
    ap.add_argument("--binary", help="Input machine-code binary; demo if omitted")
    ap.add_argument("--outdir", default="tmp/rv32i_mvp", help="Artifact output directory")
    ap.add_argument("--max-instr", type=int, default=256)
    ap.add_argument("--max-f0-lines", type=int, default=20000)
    ap.add_argument("--require", action="append", default=[], help="Require instruction name in trace (repeatable)")
    ap.add_argument("--binary-required", action="store_true", help="Fail if --binary is not provided")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[2]
    tracer = repo / "riscv-port" / "riscv_trace_to_f0.py"
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    if args.binary_required and not args.binary:
        return fail("--binary is required in this mode")

    f0_path = outdir / "program.f0"
    trace_path = outdir / "trace.json"

    cmd = [
        "python3",
        str(tracer),
        "--max-instr",
        str(args.max_instr),
        "--out",
        str(f0_path),
        "--trace-json",
        str(trace_path),
    ]
    if args.binary:
        cmd.extend(["--binary", args.binary])

    rc, so, se = run(cmd)
    (outdir / "tracer.stdout.log").write_text(so, encoding="utf-8")
    (outdir / "tracer.stderr.log").write_text(se, encoding="utf-8")
    if rc != 0:
        return fail(f"tracer failed (rc={rc}); see {outdir}")

    if not f0_path.exists() or not trace_path.exists():
        return fail("tracer did not emit required artifacts")

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    f0_lines = f0_path.read_text(encoding="utf-8").splitlines()

    if not trace:
        return fail("empty trace")
    if len(trace) > args.max_instr:
        return fail(f"trace too long: {len(trace)} > {args.max_instr}")
    if len(f0_lines) > args.max_f0_lines:
        return fail(f"f0 too large: {len(f0_lines)} lines > {args.max_f0_lines}")

    instrs = sorted({e.get("instr_name") for e in trace})
    missing = [name for name in args.require if name not in instrs]
    if missing:
        return fail(f"required instructions missing from trace: {missing}")

    # monotonic PC sanity with branch allowances: PC is always 4-byte aligned.
    for i, e in enumerate(trace):
        pc = e.get("pc")
        if not isinstance(pc, int) or (pc % 4) != 0:
            return fail(f"bad pc at trace[{i}]: {pc}")
        pca = e.get("pc_after")
        if not isinstance(pca, int) or (pca % 4) != 0:
            return fail(f"bad pc_after at trace[{i}]: {pca}")

    step_diff_rc = None
    step_diff_out = ""
    step_diff_err = ""
    if args.binary:
        step_diff = repo / "scripts" / "riscv" / "rv32i_step_diff.py"
        s_cmd = [
            "python3",
            str(step_diff),
            "--binary",
            args.binary,
            "--trace-json",
            str(trace_path),
        ]
        step_diff_rc, step_diff_out, step_diff_err = run(s_cmd)
        (outdir / "step_diff.stdout.log").write_text(step_diff_out, encoding="utf-8")
        (outdir / "step_diff.stderr.log").write_text(step_diff_err, encoding="utf-8")
        if step_diff_rc != 0:
            return fail(f"step-diff failed (rc={step_diff_rc}); see {outdir}")

    summary = {
        "ok": True,
        "trace_len": len(trace),
        "f0_lines": len(f0_lines),
        "instructions": instrs,
        "trace_sha256": trace_digest(trace),
        "step_diff_rc": step_diff_rc,
        "artifacts": {
            "f0": str(f0_path),
            "trace": str(trace_path),
            "tracer_stdout": str(outdir / "tracer.stdout.log"),
            "tracer_stderr": str(outdir / "tracer.stderr.log"),
        },
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("OK: rv32i_mvp_check")
    print(f"  trace_len={summary['trace_len']}")
    print(f"  f0_lines={summary['f0_lines']}")
    print(f"  instructions={','.join(instrs)}")
    print(f"  outdir={outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
