# Benchmark CSV schema (v0 target)

_file: doc/bench_csv_schema.md_

This document defines the **target** CSV schema for benchmark outputs.

Goal: all benchmark wrappers should converge to a stable schema so parsing/plotting is unified.

---

## Current state (today)

- Individual benchmark scripts may emit **one CSV row without a header**.
- The demo script may emit **a header + rows**.

See `doc/benchmarks.md` for the current scripts.

---

## Target format (v0)

- CSV, UTF-8
- One header line (column names)
- One row per benchmark run

### Minimal columns (v0)
Recommended columns:

- `bench` (e.g. `pack`, `permute`, `bulkcopy`)
- `name` (human-readable variant name)
- `mode` (optional string)
- `seed` (integer, optional)

- `space_bytes`
- `processor_n`
- `addr_bits`

- `ticks_total`
- `moved_bits_total` (or `moved_bytes_total`, but pick one consistently)

- `vmrep_avg_bits_uniq_dst_per_tick` (if available)
- `notes` (optional)

---

## Enforcement plan

Once the benchmark scripts are migrated to v0, we should add a small CI/TDD check that:
- the header matches exactly,
- all rows have the same number of fields.

