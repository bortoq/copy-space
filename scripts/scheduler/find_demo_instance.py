#!/usr/bin/env python3
import glob, json, os, shutil, subprocess, sys, tempfile

PY = sys.executable
SOLVE = "scripts/scheduler/solve_v0.py"
VALID = "scripts/scheduler/validate_v0.py"
OUT_INST = "scripts/scheduler/tests/demo_instance.json"

def run(inst_path, solver):
    with tempfile.TemporaryDirectory() as td:
        sched = os.path.join(td, f"{solver}.sched.json")
        rep_path = os.path.join(td, f"{solver}.report.json")

        r = subprocess.run([PY, SOLVE, inst_path, "--out", sched, "--solver", solver],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return None

        r = subprocess.run([PY, VALID, inst_path, sched, "--report", rep_path],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return None

        rep = json.load(open(rep_path, "r", encoding="utf-8"))
        if rep.get("status") != "PASS":
            return None
        return rep

paths = sorted(glob.glob("scripts/scheduler/tests/ref_pack/*.json"))
if not paths:
    print("No ref_pack instances found. Run gen_ref_pack.py first.", file=sys.stderr)
    sys.exit(1)

for p in paths:
    rb = run(p, "baseline")
    rg = run(p, "greedy")
    if not rb or not rg:
        continue
    tb = int(rb["ticks_total"])
    tg = int(rg["ticks_total"])
    if tg < tb:
        os.makedirs(os.path.dirname(OUT_INST), exist_ok=True)
        shutil.copyfile(p, OUT_INST)
        print("DEMO FOUND:", os.path.basename(p))
        print("saved to:", OUT_INST)
        print("baseline ticks_total:", tb, "util:", f"{rb['utilization']:.4f}")
        print("greedy   ticks_total:", tg, "util:", f"{rg['utilization']:.4f}")
        sys.exit(0)

print("No demo instance found where greedy < baseline (try regenerating pack / adjusting params).")
sys.exit(2)
