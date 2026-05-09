#!/usr/bin/env python3
import sys, os, json, subprocess, glob

PY = sys.executable
SOLVE = "scripts/scheduler/solve_v0.py"
VALIDATE = "scripts/scheduler/validate_v0.py"

def run_solver(inst_path, solver):
    out = inst_path + f".{solver}.sched.json"
    r = subprocess.run([PY, SOLVE, inst_path, "--out", out, "--solver", solver], capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stderr.strip()
    return out, None

def run_validate(inst_path, sched_path):
    rep = inst_path + ".report.json"
    r = subprocess.run([PY, VALIDATE, inst_path, sched_path, "--report", rep], capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stderr.strip()
    with open(rep, "r", encoding="utf-8") as f:
        return json.load(f), None

print("instance,solver,status,ticks_total,bits_total,bits_per_tick,utilization,max_degree_chunks")

better = equal = worse = 0
sum_ticks_baseline = 0
sum_ticks_greedy = 0

instances = sorted(glob.glob("scripts/scheduler/tests/ref_pack/*.json"))
for inst_path in instances:
    name = os.path.basename(inst_path)
    reps = {}

    for solver in ["baseline", "greedy"]:
        sched, err = run_solver(inst_path, solver)
        if not sched:
            print(f"{name},{solver},ERROR_SOLVE,,,,,")
            continue

        rep, err = run_validate(inst_path, sched)
        if not rep or rep.get("status") != "PASS":
            print(f"{name},{solver},ERROR_VALIDATE,,,,,")
            continue

        reps[solver] = rep
        print(f"{name},{solver},PASS,{rep['ticks_total']},{rep['bits_total']},{rep['bits_per_tick']:.2f},{rep['utilization']:.4f},{rep.get('max_degree_chunks',0)}")

        os.remove(sched)
        os.remove(inst_path + ".report.json")

    if "baseline" in reps and "greedy" in reps:
        tb = int(reps["baseline"]["ticks_total"])
        tg = int(reps["greedy"]["ticks_total"])
        sum_ticks_baseline += tb
        sum_ticks_greedy += tg
        if tg < tb: better += 1
        elif tg == tb: equal += 1
        else: worse += 1

print()
print("SUMMARY")
print("instances_total:", len(instances))
print("paired_ok:", better + equal + worse)
print("greedy_better:", better)
print("greedy_equal:", equal)
print("greedy_worse:", worse)
if (better + equal + worse) > 0:
    print("avg_ticks_baseline:", sum_ticks_baseline / (better + equal + worse))
    print("avg_ticks_greedy:", sum_ticks_greedy / (better + equal + worse))
    print("avg_ticks_delta:", (sum_ticks_baseline - sum_ticks_greedy) / (better + equal + worse))
