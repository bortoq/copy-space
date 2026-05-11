from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile


DEFAULT_INST = "scripts/scheduler/tests/demo_instance.json"


def solve_cmd() -> list[str]:
    exe = shutil.which("copyspace-solve")
    if exe:
        return [exe]
    return [sys.executable, "-c", "from copyspace.v0.solve import main; main()"]


def validate_cmd() -> list[str]:
    exe = shutil.which("copyspace-validate")
    if exe:
        return [exe]
    return [sys.executable, "-c", "from copyspace.v0.validate import main; main()"]


def run_one(inst_path: str, solver: str) -> dict:
    with tempfile.TemporaryDirectory() as td:
        sched = os.path.join(td, f"{solver}.sched.json")
        rep_path = os.path.join(td, f"{solver}.report.json")
        subprocess.check_call(solve_cmd() + [inst_path, "--out", sched, "--solver", solver])
        subprocess.check_call(validate_cmd() + [inst_path, sched, "--report", rep_path, "--quiet"])
        return json.load(open(rep_path, "r", encoding="utf-8"))


def rep_lb(rep: dict) -> int:
    return int(rep.get("lower_bound_ticks", rep.get("max_degree_chunks", 0)))


def rep_gap_ticks(rep: dict) -> int:
    if "gap_ticks" in rep:
        return int(rep["gap_ticks"])
    return int(rep.get("ticks_total", 0)) - rep_lb(rep)


def rep_gap_ratio(rep: dict) -> float:
    if "gap_to_lower_bound" in rep:
        return float(rep["gap_to_lower_bound"])
    lb = rep_lb(rep)
    gt = rep_gap_ticks(rep)
    return (gt / lb) if lb > 0 else 0.0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Scheduler demo: baseline vs greedy (STRICT1).")
    ap.add_argument("--instance", default=DEFAULT_INST, help="instance JSON path")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.instance):
        raise SystemExit("ERROR: no such instance file: " + args.instance)

    rb = run_one(args.instance, "baseline")
    rg = run_one(args.instance, "greedy")

    print("solver,ticks_total,lower_bound_ticks,gap_ticks,gap_to_lower_bound,utilization,bits_per_tick")
    print(
        f"baseline,{rb['ticks_total']},{rep_lb(rb)},{rep_gap_ticks(rb)},{rep_gap_ratio(rb):.6f},"
        f"{float(rb.get('utilization', 0.0)):.4f},{float(rb.get('bits_per_tick', 0.0)):.2f}"
    )
    print(
        f"greedy,{rg['ticks_total']},{rep_lb(rg)},{rep_gap_ticks(rg)},{rep_gap_ratio(rg):.6f},"
        f"{float(rg.get('utilization', 0.0)):.4f},{float(rg.get('bits_per_tick', 0.0)):.2f}"
    )
    print()
    print("delta_ticks_total:", int(rb["ticks_total"]) - int(rg["ticks_total"]))
    print("delta_gap_ticks:", rep_gap_ticks(rb) - rep_gap_ticks(rg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
