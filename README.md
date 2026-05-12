# Copy-Space — validated scheduling toolkit for deterministic data movement

[![CI](https://github.com/bortoq/copy-space/actions/workflows/ci.yml/badge.svg)](https://github.com/bortoq/copy-space/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/bortoq/copy-space)](https://github.com/bortoq/copy-space/releases)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.9-blue)](pyproject.toml)

Copy-Space produces conflict-free schedules for directed data transfer demands under a deterministic resource model (STRICT1).
It also provides an independent validator report with reproducible metrics.

What you get:
- Correctness: schedule validation under STRICT1 (coverage + bandwidth + model constraints)
- A lower bound on required ticks (lower_bound_ticks) and a normalized gap metric (gap_to_lower_bound)
- Reproducible metrics suitable for CI gating and regression tracking

------------------------------------------------------------

## Try it in 60 seconds (hero example)

Shuffle/materialization-like workload (8 slots):

  python3 -m venv .venv
  . .venv/bin/activate
  python -m pip install -e .
  copyspace-pilot --csv examples/shuffle8.csv --bw 256 --outdir tmp/pilot_shuffle8 --plot

Example output (expected shape):

  baseline status=PASS ticks=128 lb=128 gap=0 gapr=0.000000 util=1.0000
  greedy   status=PASS ticks=128 lb=128 gap=0 gapr=0.000000 util=1.0000

What to open after the run:
- tmp/pilot_shuffle8/report_baseline.json
- tmp/pilot_shuffle8/report_greedy.json
- tmp/pilot_shuffle8/plot_baseline.html
- tmp/pilot_shuffle8/plot_greedy.html

Bench history (smoke time series):
- https://bortoq.github.io/copy-space/

------------------------------------------------------------

## CLI entrypoints (Scheduler v0)

  copyspace-validate --help
  copyspace-solve --help
  copyspace-pilot --help
  copyspace-demo-scheduler --help
  copyspace-bench-core --help
  copyspace-bench-scheduler --help

Partner-facing docs:
- doc/partners/quickstart_pilot.md
- doc/partners/pilot_intake.md
- doc/partners/ci_gate_recipe.md

Technical contracts (source of truth):
- doc/scheduler_io_v0.md
- doc/strict1_model_v0.md

------------------------------------------------------------

## What is inside (high-level)

Scheduler v0 (pilot-facing, recommended):
- validator + metrics (copyspace-validate)
- solver strategies (copyspace-solve: baseline, greedy, external)
- pilot runner (copyspace-pilot)

Under the hood (VM and toolchain):
- minimal bit-addressable VM (space, ticks, copy slots)
- std7_fixed image builder (mkimage_std7_fixed)
- host-side Forth0 compiler (forth0c) and Forth0-first regression tests

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
