# Contributing

Thanks for considering contributing to Copy-Space.

This repo contains two layers:
- Scheduler v0 toolkit (pilot-facing, recommended): validated scheduling under STRICT1 with reproducible metrics
- DPF VM and toolchain (under the hood): native tools, Forth0-first tests, VM-level benchmarks

For stable interfaces and contracts see:
- doc/scheduler_io_v0.md
- doc/strict1_model_v0.md
- doc/status.md

------------------------------------------------------------

## Quick checks (before opening a PR)

From repo root:

1) Build:
   make bins

2) Non-TDD tests:
   make test

3) TDD:
   make tdd

4) Scheduler tests:
   ./scripts/test_scheduler.sh

Optional (local smoke benches, Python-first entrypoints):
- python3 -m pip install -e .
- copyspace-bench-core --bench all --out tmp/bench_smoke.csv --repeat 1
- copyspace-bench-scheduler --out tmp/sched_smoke.csv --repeat 1 --inst-glob scripts/scheduler/tests/demo_instance.json

CI notes:
- Heavy jobs (bench-smoke, stress-smoke) run on push to main and workflow_dispatch, and are skipped on pull_request.

------------------------------------------------------------

## Scheduler v0 notes

Preferred user-facing entrypoints (installed via python3 -m pip install -e .):
- copyspace-validate
- copyspace-solve
- copyspace-pilot
- copyspace-bench-core
- copyspace-bench-scheduler

Internal scripts exist as wrappers for development and CI.

Useful links:
- I/O contract: doc/scheduler_io_v0.md
- Demo (python-first): copyspace-demo-scheduler
- One-command pilot: copyspace-pilot --csv examples/demands.csv --bw 256 --outdir tmp/pilot

------------------------------------------------------------

## Adding a new scheduler instance (reference pack)

Reference pack lives in:
  scripts/scheduler/tests/ref_pack/

You can regenerate the seeded pack:
  python3 scripts/scheduler/gen_ref_pack.py

If you add a new hand-crafted instance, please also:
- include a short note in the JSON (notes field)
- ensure baseline and greedy solvers validate on it
- keep it small and reproducible

------------------------------------------------------------

## Reporting bugs

Please include:
- instance.json
- schedule.json (or demands CSV)
- validator report JSON (copyspace-validate --report report.json)
- exact commands to reproduce
- OS, Python version, git revision (or copy-space version)

------------------------------------------------------------

## Style

- Keep changes focused and easy to review.
- Prefer deterministic behavior (or fixed recorded seeds).
- Update doc/status.md when changes are substantial (new tools, new workflows, new guarantees).

If you change GitHub Actions workflows:
- keep Python pinned to a stable version
- ensure workflow_dispatch behavior matches doc/status.md and doc/roadmap.md
