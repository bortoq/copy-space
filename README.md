# Copy-Space — validated scheduling toolkit for deterministic data movement

Copy-Space is a deterministic toolkit for validated scheduling of data movement.
Given transfer demands and a resource model, it produces a conflict-free schedule plus an independent validator
report with reproducible metrics.

Primary use cases (pilot-facing):
- CI gating: schedule correctness checks plus performance regression limits
- Benchmarking: compare scheduling strategies with reproducible metrics

Key differentiator:
- The validator reports a theoretical lower bound on required ticks (lower_bound_ticks)
- It also reports a normalized gap metric: gap_to_lower_bound
This makes it possible to track how far a schedule is from the best possible result under the model.

------------------------------------------------------------

## Start here (Scheduler v0)

Install (optional, enables copyspace-* CLI entrypoints):

  python3 -m venv .venv
  . .venv/bin/activate
  python -m pip install -e .

CLI entrypoints:

  copyspace-validate --help
  copyspace-solve --help
  copyspace-pilot --help

Demo (baseline vs greedy, prints lower bound + gap):

  python3 scripts/scheduler/demo_run.py

One-command pilot (CSV -> instance -> schedules -> reports):

  copyspace-pilot --csv examples/demands.csv --bw 256 --outdir tmp/pilot

Partner-facing docs:
- doc/partners/quickstart_pilot.md
- doc/partners/pilot_intake.md
- doc/partners/ci_gate_recipe.md

Technical contracts (source of truth):
- doc/scheduler_io_v0.md
- doc/strict1_model_v0.md

------------------------------------------------------------

## What is inside (high-level)

Scheduler v0 (recommended for pilots and external users):
- schedule validator + metrics (copyspace-validate)
- solver strategies for comparison (copyspace-solve: baseline, greedy, external)
- pilot runner for onboarding (copyspace-pilot)
- adapters:
  - CSV demands -> instance (copyspace-csv-to-instance)
  - text lines -> schedule JSON (copyspace-lines-to-schedule)

Under the hood (research VM and toolchain):
- a minimal bit-addressable VM (space, ticks, copy slots)
- a baseline image builder (mkimage_std7_fixed)
- a host-side Forth0 compiler (forth0c) and Forth0-first regression tests
- benchmarks and vmrep-based throughput metrics (CSV)

If you are a pilot partner evaluating validated scheduling, you do not need the VM toolchain to start.
Use the Scheduler v0 entrypoints above.

------------------------------------------------------------

## Optional: VM demo (DB / analytics focus)

Build native tools:

  make bins

Run demo (produces CSV):

  scripts/demo_db.sh > /dev/null 2> tmp/demo.stderr
  cat tmp/demo.csv

Key metric in CSV:

  vmrep_avg_bits_uniq_dst_per_tick

Meaning:
- effective unique destination bits written per tick (useful write throughput)

------------------------------------------------------------

## Tests

Run all regression tests:

  make test
  make tdd

Scheduler v0 fixtures and smokes:
- scripts/test_scheduler.sh
- scripts/scheduler/tests

------------------------------------------------------------

## Documentation

Start here:

- doc/README.md

Status and roadmap:

- doc/status.md
- doc/roadmap.md

------------------------------------------------------------

## License

Apache-2.0 — see LICENSE
Third-party notes — see THIRD_PARTY.md

------------------------------------------------------------

## Contact

Dmitri Bortoq
Email: bortoq@gmail.com
Telegram: @the_arctium
GitHub repo: https://github.com/bortoq/copy-space
