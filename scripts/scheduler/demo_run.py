#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile

PY = sys.executable
SOLVE = "scripts/scheduler/solve_v0.py"
VALID = "scripts/scheduler/validate_v0.py"
INST = "scripts/scheduler/tests/demo_instance.json"

def run(solver: str) -> dict:
    with tempfile.TemporaryDirectory() as td:
        sched = os.path.join(td, f"{solver}.sched.json")
        rep_path = os.path.join(td, f"{solver}.report.json")
        subprocess.check_call([PY, SOLVE, INST, "--out", sched, "--solver", solver])
        subprocess.check_call([PY, VALID, INST, sched, "--report", rep_path])

        with open(rep_path, "r", encoding="utf-8") as f:
            return json.load(f)

def rep_lb(rep: dict) -> int:
    # backward compatible with older reports
    return int(rep.get("lower_bound_ticks", rep.get("max_degree_chunks", 0)))

def rep_gap_ticks(rep: dict) -> int:
    if "gap_ticks" in rep:
        return int(rep["gap_ticks"])
    return int(rep["ticks_total"]) - rep_lb(rep)

def rep_gap_ratio(rep: dict) -> float:
    if "gap_to_lower_bound" in rep:
        return float(rep["gap_to_lower_bound"])
    lb = rep_lb(rep)
    return (rep_gap_ticks(rep) / lb) if lb > 0 else 0.0

rb = run("baseline")
rg = run("greedy")

print("solver,ticks_total,lower_bound_ticks,gap_ticks,gap_to_lower_bound,utilization,bits_per_tick")
print(
    f"baseline,{rb['ticks_total']},{rep_lb(rb)},{rep_gap_ticks(rb)},{rep_gap_ratio(rb):.6f},"
    f"{rb['utilization']:.4f},{rb['bits_per_tick']:.2f}"
)
print(
    f"greedy,{rg['ticks_total']},{rep_lb(rg)},{rep_gap_ticks(rg)},{rep_gap_ratio(rg):.6f},"
    f"{rg['utilization']:.4f},{rg['bits_per_tick']:.2f}"
)
print()
print("delta_ticks_total:", int(rb["ticks_total"]) - int(rg["ticks_total"]))
print("delta_gap_ticks:", rep_gap_ticks(rb) - rep_gap_ticks(rg))
