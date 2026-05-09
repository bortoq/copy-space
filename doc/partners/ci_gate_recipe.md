# CI gate recipe (v0, real commands)

This document shows a CI gating pattern Copy-Space targets (Pain A) using **real** repository commands.

Model assumptions: STRICT1, volume-based I/O v0.

## Gate 1: correctness (validator must pass)

If you already have a schedule artifact (validate-only workflow):

    python3 scripts/scheduler/validate_v0.py INSTANCE.json SCHEDULE.json --report report.json
    echo $?

Exit codes:
- 0: PASS
- 2: FAIL (invalid schedule / coverage mismatch / extras)
- 1: parse/usage error

## Gate 2: performance regression (ticks_total must not regress beyond threshold)

Store a baseline report (or baseline metrics) in your repo/artifacts, e.g. baseline_report.json.

Example gate (ticks_total +2% max, utilization floor optional):

    python3 - <<'PY'
    import json, sys

    base = json.load(open("baseline_report.json", "r", encoding="utf-8"))
    cur  = json.load(open("report.json", "r", encoding="utf-8"))

    if cur.get("status") != "PASS":
        print("FAIL: current report is not PASS")
        sys.exit(2)

    base_ticks = int(base["ticks_total"])
    cur_ticks  = int(cur["ticks_total"])

    # policy: allow up to +2% regression
    if cur_ticks > int(base_ticks * 1.02 + 0.999):
        print(f"REGRESSION: ticks_total {cur_ticks} > baseline {base_ticks} * 1.02")
        sys.exit(3)

    # optional utilization floor
    util_floor = 0.30
    cur_util = float(cur.get("utilization", 0.0))
    if cur_util < util_floor:
        print(f"REGRESSION: utilization {cur_util:.4f} < {util_floor}")
        sys.exit(4)

    print("OK: no regression beyond thresholds")
    PY

## Optional: generate schedules in CI (baseline vs improved)

If you want Copy-Space to generate candidate schedules:

    python3 scripts/scheduler/solve_v0.py INSTANCE.json --out schedule_baseline.json --solver baseline
    python3 scripts/scheduler/validate_v0.py INSTANCE.json schedule_baseline.json --report report_baseline.json

    python3 scripts/scheduler/solve_v0.py INSTANCE.json --out schedule_greedy.json --solver greedy
    python3 scripts/scheduler/validate_v0.py INSTANCE.json schedule_greedy.json --report report_greedy.json

Then compare the reports (ticks_total/utilization) and choose a policy:
- gate on baseline only (regression tracking)
- or gate on “best of two” (if your process allows solver choice)
