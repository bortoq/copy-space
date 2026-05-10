# Contributing

Thanks for considering contributing to Copy-Space.

This repo contains:
- a Forth0 toolchain baseline (tests + CI)
- scheduler v0 tooling (validated scheduling under STRICT1, volume-based)

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

Optional (smoke benches):
- scripts/bench/run.sh --bench scheduler --out tmp/sched.csv --repeat 1
- python3 scripts/bench/summarize.py --in tmp/sched.csv --top 5

## Scheduler v0 notes

- I/O contract: doc/scheduler_io_v0.md
- Demo: python3 scripts/scheduler/demo_run.py
- One-command pilot: ./scripts/scheduler/pilot_run.sh --csv examples/demands.csv --bw 256 --outdir tmp/pilot

## Adding a new scheduler instance (reference pack)

Reference pack lives in:
  scripts/scheduler/tests/ref_pack/

You can regenerate the seeded pack:
  python3 scripts/scheduler/gen_ref_pack.py

If you add a new hand-crafted instance, please also:
- include a short note in the JSON (notes field)
- ensure both solvers pass validation on it
- keep it small and reproducible

## Reporting bugs

Please include:
- Instance JSON
- Schedule JSON (or demands CSV)
- Validator report JSON (if available)
- commands to reproduce
- OS + Python version + git revision

## Style

- Keep changes focused and easy to review.
- Prefer deterministic behavior (or fixed recorded seeds).
- Update doc/status.md when changes are substantial (new tools, new workflows, new guarantees).
