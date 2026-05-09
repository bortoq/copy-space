#!/usr/bin/env python3
import json, os, subprocess, sys, tempfile

PY = sys.executable
SOLVE = "scripts/scheduler/solve_v0.py"
VALID = "scripts/scheduler/validate_v0.py"
INST = "scripts/scheduler/tests/demo_instance.json"

def run(solver):
    with tempfile.TemporaryDirectory() as td:
        sched = os.path.join(td, f"{solver}.sched.json")
        rep_path = os.path.join(td, f"{solver}.report.json")
        subprocess.check_call([PY, SOLVE, INST, "--out", sched, "--solver", solver])
        subprocess.check_call([PY, VALID, INST, sched, "--report", rep_path])
        return json.load(open(rep_path, "r", encoding="utf-8"))

rb = run("baseline")
rg = run("greedy")

print("solver,ticks_total,utilization,bits_per_tick,max_degree_chunks")
print(f"baseline,{rb['ticks_total']},{rb['utilization']:.4f},{rb['bits_per_tick']:.2f},{rb.get('max_degree_chunks',0)}")
print(f"greedy,{rg['ticks_total']},{rg['utilization']:.4f},{rg['bits_per_tick']:.2f},{rg.get('max_degree_chunks',0)}")
print()
print("delta_ticks_total:", int(rb["ticks_total"]) - int(rg["ticks_total"]))
