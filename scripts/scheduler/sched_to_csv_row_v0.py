#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
import time
from typing import Dict, List

PY = sys.executable

VMREP_HEADER = [PY, "scripts/vmrep_to_csv.py", "--header"]
SOLVE = [PY, "scripts/scheduler/solve_v0.py"]
VALIDATE = [PY, "scripts/scheduler/validate_v0.py"]

def sh(cmd: List[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()

def try_git_rev() -> str:
    try:
        return sh(["git", "rev-parse", "--short", "HEAD"])
    except Exception:
        return ""

def get_header_cols() -> List[str]:
    line = sh(VMREP_HEADER)
    return next(csv.reader([line]))

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def run(instance_path: str, solver: str) -> Dict[str, str]:
    inst = load_json(instance_path)
    slots = int(inst["slots"])
    bw = int(inst["copy_bw_bits_per_tick"])
    mode = os.path.basename(instance_path)

    with tempfile.TemporaryDirectory() as td:
        sched_path = os.path.join(td, "sched.json")
        rep_path = os.path.join(td, "report.json")

        # solve
        t0 = time.perf_counter()
        subprocess.check_call(SOLVE + [instance_path, "--out", sched_path, "--solver", solver])
        t1 = time.perf_counter()
        solve_ms = (t1 - t0) * 1000.0


        # validate + report
        # validate_v0 returns 0 on PASS; coverage is enforced by default if demands non-empty
        t0 = time.perf_counter()
        subprocess.check_call(VALIDATE + [instance_path, sched_path, "--report", rep_path, "--quiet"])
        t1 = time.perf_counter()
        validate_ms = (t1 - t0) * 1000.0


        sched = load_json(sched_path)
        rep = load_json(rep_path)

        ticks_total = int(rep["ticks_total"])
        bits_total = int(rep["bits_total"])
        bpt = float(rep["bits_per_tick"])
        exp_bpt = int(rep["expected_bits_per_tick"])
        util = float(rep["utilization"])
        lb = int(rep.get("lower_bound_ticks", rep.get("max_degree_chunks", 0)))
        gap_ticks = ticks_total - lb
        gap_ratio = (gap_ticks / lb) if lb > 0 else 0.0

        copies_total = 0
        for tick in sched.get("ticks", []):
            copies_total += len(tick)

    # Build a row dict in the unified CSV schema (fill only known columns; others remain "-")
    row: Dict[str, str] = {}
    row["schema_version"] = "0"
    row["bench"] = "scheduler"
    row["mode"] = mode
    row["seed"] = "0"
    row["space_bytes"] = "0"
    row["slots"] = str(slots)
    row["addr_bits"] = "0"
    row["ticks_total"] = str(ticks_total)
    row["moved_bits_total"] = str(bits_total)

    # Reuse vmrep columns to make summarize.py work unchanged:
    # treat bits_per_tick as the "throughput" to rank and to compute util vs expected_bits_per_tick.
    row["vmrep_avg_bits_sum_per_tick"] = f"{bpt:.6f}"
    row["vmrep_avg_bits_uniq_dst_per_tick"] = f"{bpt:.6f}"

    row["copies_total"] = str(copies_total)
    row["expected_bits_per_tick"] = str(exp_bpt)

    row["notes"] = (
        f"solver={solver};lb={lb};gap={gap_ticks};gap_ratio={gap_ratio:.6f};bw={bw};util={util:.6f};"
        f"solve_ms={solve_ms:.3f};validate_ms={validate_ms:.3f}"
    )
    row["git_rev"] = try_git_rev()

    return row

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", required=True)
    ap.add_argument("--solver", required=True, choices=["baseline", "greedy"])
    args = ap.parse_args()

    cols = get_header_cols()
    row = {c: "-" for c in cols}
    row.update(run(args.instance, args.solver))

    w = csv.writer(sys.stdout, lineterminator="\n")
    w.writerow([row.get(c, "-") for c in cols])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
