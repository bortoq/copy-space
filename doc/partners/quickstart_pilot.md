# Quickstart (pilot v0)

This quickstart shows an end-to-end workflow for a pilot:
CSV demands -> Instance v0 -> Solve -> Validate -> Reports.

## 0) Inputs
- demands.csv:
  src_slot,dst_slot,bits_total
  0,1,4096
  2,3,256

- copy_bw_bits_per_tick (example): 256

## 1) Convert CSV -> Instance v0
    python3 scripts/scheduler/csv_to_instance_v0.py demands.csv --bw 256 --out instance.json

(Optionally set slots explicitly)
    python3 scripts/scheduler/csv_to_instance_v0.py demands.csv --bw 256 --slots 32 --out instance.json

## 2) Solve (baseline and greedy)
    python3 scripts/scheduler/solve_v0.py instance.json --out schedule_baseline.json --solver baseline
    python3 scripts/scheduler/solve_v0.py instance.json --out schedule_greedy.json --solver greedy

## 3) Validate + produce reports
    python3 scripts/scheduler/validate_v0.py instance.json schedule_baseline.json --report report_baseline.json
    python3 scripts/scheduler/validate_v0.py instance.json schedule_greedy.json --report report_greedy.json

Exit codes:
- 0: PASS
- 2: FAIL
- 1: parse/usage error

## 4) Compare key metrics (example)
    python3 - <<'PY'
    import json
    b = json.load(open("report_baseline.json"))
    g = json.load(open("report_greedy.json"))
    print("baseline ticks_total:", b["ticks_total"], "util:", round(b["utilization"], 4))
    print("greedy   ticks_total:", g["ticks_total"], "util:", round(g["utilization"], 4))
    print("delta_ticks_total:", int(b["ticks_total"]) - int(g["ticks_total"]))
    PY

## 5) Run the public reference pack benchmark (optional)
    python3 scripts/scheduler/gen_ref_pack.py
    python3 scripts/scheduler/bench_v0.py | tail -n 40
