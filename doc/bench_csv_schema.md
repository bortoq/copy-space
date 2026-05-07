# Benchmark CSV schema (v0)

_file: doc/bench_csv_schema.md_

This document defines the **stable CSV schema** for benchmark outputs.

Goal: all benchmark wrappers should emit the same header and the same columns, so that parsing/plotting is unified.

## Format
- CSV, UTF-8
- One header line (column names)
- One row per benchmark run

## Minimal columns (v0)
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

## Compatibility note
Current scripts may still evolve. The goal is to converge to this schema as part of TODO C.

