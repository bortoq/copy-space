# Copy-Space / Deterministic Data Movement Fabric (DPF)

**Pitch (short):** Copy-Space is a deterministic toolkit for **validated scheduling** of data movement.
Given transfer demands and a resource model, it produces a conflict-free schedule plus an independent validator
report with reproducible metrics.

**Key differentiator:** the validator reports a theoretical **lower bound** on required ticks
(`lower_bound_ticks`, derived from per-slot degree in chunks) and a normalized gap metric:
`gap_to_lower_bound = (ticks_total - lower_bound_ticks) / lower_bound_ticks`.
This makes it possible to track “how far from the best possible (under the model)” a schedule is.

---

## Scheduler quickstart

[![asciicast](https://asciinema.org/a/3MmAYdSZq67fneOs.svg)](https://asciinema.org/a/3MmAYdSZq67fneOs)

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

More:
- doc/partners/quickstart_pilot.md
- doc/partners/pilot_intake.md

_file: README.md_

Copy-Space treats computation as scheduled bit-copies executed in fixed ticks, making throughput and scheduling
constraints explicit. This is useful for workloads dominated by memory movement (compaction, reorder/permute,
partition/materialization).

The core operation is:

    copy(n, dst, src)

All higher-level behavior is built by composing this primitive (plus a small baseline image: `std7_fixed`).

## What’s inside (high-level)

- A minimal bit-addressable VM (`space`, ticks, copy slots)
- A baseline image builder: `mkimage_std7_fixed`
- A host-side `.f0` compiler: `forth0c` (Forth0-first workflow)
- A deterministic testing pipeline (`make test`, `make tdd`, CI)
- Benchmarks and vmrep-based throughput metrics (CSV)
- Scheduler v0 tooling (solve + validate + metrics, incl. lower bound + gap)

---

## Quick Demo (DB / Analytics Focus)

Build tools:

    make bins

Run demo (produces CSV):

    scripts/demo_db.sh > /dev/null 2> tmp/demo.stderr
    cat tmp/demo.csv

Key metric in CSV:

    vmrep_avg_bits_uniq_dst_per_tick

This is effective unique destination bits written per tick (useful write throughput).

---

## Forth0-first workflow (recommended)

This repo uses **host-compiled Forth0** for most tests and higher-level logic:

- `.f0` text program → `build/bin/forth0c` → `.tok` stream
- VM compile phase (`vmrun`) → `vmprep_forth0` → VM run phase (`vmrun`)

Docs:

- `doc/forth0.md`

Run a `.f0` program and dump `TESTG`:

    scripts/forth0/run_f0.sh --in src/forth0/tests/test_eq24.f0 --dump-testg 4

Strict alignment check for block pointers (`LITAP/LITBP/LITRP` immediates must be 32-bit aligned):

    F0C_STRICT_ALIGN32=1 build/bin/forth0c --image std7.bin --in prog.f0 --out prog.tok

---

## Tests

Run all tests:

    make test
    make tdd

Legacy C token-generators (`build/bin/mktok_test_*`) are **optional**:

    make tok
    # or
    make TOK=1 bins

---

## Documentation

Start here:

- `doc/README.md`

Status / roadmap:

- `doc/status.md`
- `doc/roadmap.md`

---

## License

Apache-2.0 — see LICENSE  
Third-party notes — see THIRD_PARTY.md

---

## Contact

Dmitri Bortoq  
Email: bortoq@gmail.com  
Telegram: @the_arctium  
GitHub repo: https://github.com/bortoq/copy-space
