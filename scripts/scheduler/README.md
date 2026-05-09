# Scheduler scripts (v0)

This directory contains a minimal v0 toolchain for:
- solving a volume-based full-mesh transfer scheduling problem (STRICT1),
- validating schedules (including coverage vs demands),
- benchmarking baseline vs improved strategies.

## Quick demo (baseline vs greedy)
    python3 scripts/scheduler/demo_run.py

## Validate a schedule (validate-only workflow)
    python3 scripts/scheduler/validate_v0.py INSTANCE.json SCHEDULE.json --report report.json
    echo $?

Exit codes:
- 0: PASS
- 2: FAIL (invalid schedule / coverage mismatch / extras)
- 1: parse/usage error
## Solve an instance
    python3 scripts/scheduler/solve_v0.py INSTANCE.json --out schedule.json --solver baseline
    python3 scripts/scheduler/solve_v0.py INSTANCE.json --out schedule.json --solver greedy

## Run tests
    ./scripts/test_scheduler.sh

## Reference pack benchmark
    python3 scripts/scheduler/gen_ref_pack.py
    python3 scripts/scheduler/bench_v0.py | tail -n 40
