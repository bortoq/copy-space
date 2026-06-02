#!/usr/bin/env python3
"""Run local external RV32I corpus via rv32i_mvp_check.py."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(cmd):
    p = subprocess.run(cmd, text=True, capture_output=True)
    return p.returncode, p.stdout, p.stderr


def main() -> int:
    ap = argparse.ArgumentParser(description="Run external RV32I corpus")
    ap.add_argument("--manifest", default="third_party/riscv-external/manifest_rv32i.json")
    ap.add_argument("--outdir", default="tmp/rv32i_external")
    ap.add_argument("--fail-on-missing", action="store_true")
    ap.add_argument("--with-vm-run", action="store_true", help="Run VM-level check for each case")
    ap.add_argument("--max-cases", type=int, default=0, help="Limit number of cases (0 = all)")
    ap.add_argument("--allow-failures-file", default="", help="JSON file with allowed failing case names")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[2]
    manifest = repo / args.manifest
    outdir = repo / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    if not manifest.exists():
        if args.fail_on_missing:
            print(f"FAIL: manifest missing: {manifest}", file=sys.stderr)
            return 1
        print(f"SKIP: manifest missing: {manifest}")
        return 0

    data = json.loads(manifest.read_text(encoding="utf-8"))
    cases = data.get("cases", [])
    if not isinstance(cases, list) or not cases:
        print("SKIP: manifest has no cases")
        return 0

    checker = repo / "scripts" / "riscv" / "rv32i_mvp_check.py"
    allowed_failures = set()
    if args.allow_failures_file:
        af = repo / args.allow_failures_file
        if af.exists():
            raw = json.loads(af.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                names = raw.get("allowed_failures", [])
            else:
                names = raw
            if isinstance(names, list):
                allowed_failures = {str(x) for x in names}
    failures = []
    skipped = []
    waived = []
    ran = 0

    picked = cases if args.max_cases <= 0 else cases[:args.max_cases]
    for c in picked:
        name = c["name"]
        rel_bin = c["binary"]
        req = c.get("require", [])
        max_instr = int(c.get("max_instr", 256))
        bin_path = repo / rel_bin
        if not bin_path.exists():
            skipped.append({"name": name, "reason": f"missing binary: {bin_path}"})
            continue

        c_out = outdir / name
        c_out.mkdir(parents=True, exist_ok=True)
        cmd = [
            "python3",
            str(checker),
            "--binary",
            str(bin_path),
            "--binary-required",
            "--max-instr",
            str(max_instr),
            "--outdir",
            str(c_out),
        ]
        if not args.with_vm_run:
            cmd.append("--skip-vm-run")
        for r in req:
            cmd.extend(["--require", r])
        rc, so, se = run(cmd)
        (c_out / "runner.stdout.log").write_text(so, encoding="utf-8")
        (c_out / "runner.stderr.log").write_text(se, encoding="utf-8")
        ran += 1
        if rc != 0:
            err = {"name": name, "error": f"rv32i_mvp_check rc={rc}"}
            if name in allowed_failures:
                waived.append(err)
            else:
                failures.append(err)

    summary = {
        "ok": len(failures) == 0,
        "manifest": str(manifest),
        "ran": ran,
        "skipped": skipped,
        "waived": waived,
        "failures": failures,
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if failures:
        print(f"FAIL: rv32i external corpus failed; see {outdir/'summary.json'}", file=sys.stderr)
        return 1
    print(f"OK: rv32i external corpus (ran={ran}, skipped={len(skipped)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
