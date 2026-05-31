# Copy-Space — in-space computation demo platform (single-goal mode)

[![CI](https://github.com/bortoq/copy-space/actions/workflows/ci.yml/badge.svg)](https://github.com/bortoq/copy-space/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/bortoq/copy-space)](https://github.com/bortoq/copy-space/releases)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.9-blue)](pyproject.toml)

Primary goal: demonstrate non-trivial computation running inside Copy-Space address space.
RISC-V porting (`trace -> .f0 -> .tok -> VM`) is the active path to that goal.

Current focus:
- VM core stability and diagnostics
- RV32I MVP staged gates and repeatability
- end-to-end in-space computation demos

Single-goal operating mode:
- doc/MINIMAL_PATH.md

------------------------------------------------------------

## Try it in 60 seconds (RV32I minimal gate)

  make bins
  scripts/tdd/run_rv32i_minimal.sh

------------------------------------------------------------

## CLI entrypoints (active)

  riscv-port/run_riscv_f0.sh --help
  python3 scripts/riscv/rv32i_mvp_check.py --help
  scripts/riscv/run_staged_plan.sh

------------------------------------------------------------

## What is inside (high-level, current)

Core (active):
- minimal bit-addressable VM (space, ticks, copy slots)
- std7_fixed builder + host-side Forth0 pipeline
- RISC-V C2 tooling and staged RV32I MVP checks

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
