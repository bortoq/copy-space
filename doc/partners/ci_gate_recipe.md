# CI gate recipe (v0, real commands)

This document shows a CI gating pattern Copy-Space targets (Pain A) using real commands.

Model assumptions: STRICT1, volume-based I/O v0.

Live workflow example (copy-paste):
- file: doc/partners/ci_gate_workflow_example.yml
- usage: copy it into your repo as .github/workflows/copyspace_ci_gate.yml and adjust the env variables inside

Tip: use the quiet flag to suppress PASS/FAIL prints in CI logs (reports still get written).

------------------------------------------------------------

## Gate 1: correctness (validator must pass)

If you already have a schedule artifact (validate-only workflow):

    copyspace-validate INSTANCE.json SCHEDULE.json --report report.json --quiet
    echo $?

Exit codes:
- 0: PASS
- 2: FAIL (invalid schedule / coverage mismatch / extras)
- 1: parse/usage error

------------------------------------------------------------

## Gate 2: performance regression (ticks_total must not regress beyond threshold)

Store a baseline report (or baseline metrics) in your repo or in CI artifacts, e.g. baseline_report.json.

Example gate (ticks_total threshold; optional utilization and gap-to-lower-bound thresholds):

    python - <<'PY'
    import json, math, sys

    def load(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    base = load("baseline_report.json")
    cur  = load("report.json")

    if cur.get("status") != "PASS":
        print("FAIL: current report is not PASS")
        sys.exit(2)

    base_ticks = int(base["ticks_total"])
    cur_ticks  = int(cur["ticks_total"])

    # policy: allow up to +2% ticks_total regression
    allowed_pct = 2.0
    limit = int(math.floor(base_ticks * (1.0 + allowed_pct / 100.0) + 1e-9))

    if cur_ticks > limit:
        print(f"REGRESSION: ticks_total {cur_ticks} > limit {limit} (baseline {base_ticks}, allowed {allowed_pct:.1f}%)")
        sys.exit(3)

    # optional utilization floor
    util_floor = 0.30
    cur_util = float(cur.get("utilization", 0.0))
    if cur_util < util_floor:
        print(f"REGRESSION: utilization {cur_util:.4f} < {util_floor}")
        sys.exit(4)

    # optional gap-to-lower-bound ceiling (lower is better)
    # requires reports that include gap_to_lower_bound (Copy-Space validator provides it)
    gap_ceiling = 0.10
    cur_gap = float(cur.get("gap_to_lower_bound", 0.0))
    if cur_gap > gap_ceiling:
        print(f"REGRESSION: gap_to_lower_bound {cur_gap:.6f} > {gap_ceiling}")
        sys.exit(5)

    print("OK: no regression beyond thresholds")
    PY

------------------------------------------------------------

## Optional: generate schedules in CI (baseline vs improved)

If you want Copy-Space to generate candidate schedules:

    copyspace-solve INSTANCE.json --out schedule_baseline.json --solver baseline
    copyspace-validate INSTANCE.json schedule_baseline.json --report report_baseline.json --quiet

    copyspace-solve INSTANCE.json --out schedule_greedy.json --solver greedy
    copyspace-validate INSTANCE.json schedule_greedy.json --report report_greedy.json --quiet

Then compare the reports and choose a policy:
- gate on baseline only (regression tracking against your established baseline)
- or gate on best of two (if your process allows solver choice)
