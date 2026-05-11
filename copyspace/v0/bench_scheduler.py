from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Dict, List


COLS = [
    "schema_version",
    "bench",
    "mode",
    "seed",
    "space_bytes",
    "slots",
    "addr_bits",
    "ticks_total",
    "moved_bits_total",
    "vmrep_bits_sum_total",
    "vmrep_bits_uniq_dst_total",
    "vmrep_avg_bits_sum_per_tick",
    "vmrep_avg_bits_uniq_dst_per_tick",
    "thr_from",
    "thr_len",
    "thr_avg_bits_sum_per_tick",
    "thr_avg_bits_uniq_dst_per_tick",
    "notes",
    "git_rev",
    "copies_total",
    "expected_bits_per_tick",
]


def sh(cmd: List[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def try_git_rev() -> str:
    try:
        return sh(["git", "rev-parse", "--short", "HEAD"])
    except Exception:
        return ""


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_list(xs: List[str]) -> List[str]:
    out: List[str] = []
    for x in xs:
        for p in x.replace(",", " ").split():
            if p:
                out.append(p)
    return out


def solve_cmd() -> List[str]:
    exe = shutil.which("copyspace-solve")
    if exe:
        return [exe]
    # dev fallback: run entrypoint via current Python without requiring pip install -e .
    return [sys.executable, "-c", "from copyspace.v0.solve import main; main()"]


def validate_cmd() -> List[str]:
    exe = shutil.which("copyspace-validate")
    if exe:
        return [exe]
    return [sys.executable, "-c", "from copyspace.v0.validate import main; main()"]


def solve_instance(instance_path: str, sched_path: str, solver: str) -> None:
    argv = solve_cmd() + [instance_path, "--out", sched_path, "--solver", solver]
    subprocess.check_call(argv)


def validate_instance(instance_path: str, sched_path: str, rep_path: str) -> None:
    argv = validate_cmd() + [instance_path, sched_path, "--report", rep_path, "--quiet"]
    subprocess.check_call(argv)


def run_one(instance_path: str, solver: str) -> Dict[str, str]:
    inst = load_json(instance_path)
    slots = int(inst["slots"])
    bw = int(inst["copy_bw_bits_per_tick"])
    mode = os.path.basename(instance_path)

    with tempfile.TemporaryDirectory() as td:
        sched_path = os.path.join(td, "sched.json")
        rep_path = os.path.join(td, "report.json")

        t0 = time.perf_counter()
        solve_instance(instance_path, sched_path, solver)
        t1 = time.perf_counter()
        solve_ms = (t1 - t0) * 1000.0

        t0 = time.perf_counter()
        validate_instance(instance_path, sched_path, rep_path)
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

    row: Dict[str, str] = {}
    row["schema_version"] = "csv.v0"
    row["bench"] = "scheduler"
    row["mode"] = mode
    row["seed"] = "0"
    row["space_bytes"] = "0"
    row["slots"] = str(slots)
    row["addr_bits"] = "0"
    row["ticks_total"] = str(ticks_total)
    row["moved_bits_total"] = str(bits_total)

    # reuse vmrep columns so summarize.py works unchanged
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
    ap = argparse.ArgumentParser(description="Scheduler bench -> unified CSV v0 (Python-first, no shell).")
    ap.add_argument("--out", required=True, help="output CSV path (overwritten)")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument(
        "--solver-list",
        nargs="+",
        default=["baseline", "greedy"],
        help="solvers to run (space/comma-separated; default: baseline greedy)",
    )
    ap.add_argument(
        "--inst-glob",
        nargs="+",
        default=["scripts/scheduler/tests/demo_instance.json"],
        help="instance glob(s) (default: scripts/scheduler/tests/demo_instance.json)",
    )
    args = ap.parse_args()

    solvers = parse_list(args.solver_list)
    for s in solvers:
        if s not in ["baseline", "greedy", "external"]:
            raise SystemExit("ERROR: unsupported solver: " + s)

    inst_paths: List[str] = []
    for g in args.inst_glob:
        inst_paths.extend(glob.glob(g))
    inst_paths = sorted({p for p in inst_paths if os.path.isfile(p)})
    if not inst_paths:
        raise SystemExit("ERROR: no instances matched --inst-glob")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(COLS)

        for inst in inst_paths:
            for solver in solvers:
                for _ in range(args.repeat):
                    row = {c: "-" for c in COLS}
                    row.update(run_one(inst, solver))
                    w.writerow([row.get(c, "-") for c in COLS])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
