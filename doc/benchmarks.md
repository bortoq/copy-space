# Benchmarks and Metrics

_file: doc/benchmarks.md_

This repo includes throughput benchmarks and a small reporting toolchain.

CSV schema (v0):
- bench_csv_schema.md
- header source of truth: python3 scripts/vmrep_to_csv.py --header

------------------------------------------------------------

## Benchmarks

- pack:
  compaction-like benchmark (sparse source -> dense destination).
  Useful mental model: filter result compaction in DB/analytics.

- permute:
  reorder-like benchmark (chunk permutation).
  Useful mental model: reorder, partition, materialization.

- bulkcopy:
  large contiguous copy per tick (upper bound style benchmark).

------------------------------------------------------------

## Run benchmarks (Python-first, recommended)

Core benches (pack, permute, bulkcopy) use the python-first entrypoint:
- copyspace-bench-core

Run all core benches into one CSV file:

    copyspace-bench-core --bench all --out tmp/bench.csv
    head -5 tmp/bench.csv

Run just one:

    copyspace-bench-core --bench pack --out tmp/pack.csv

Scheduler bench (validated scheduling, unified CSV):

    copyspace-bench-scheduler --out tmp/sched.csv --repeat 1 --inst-glob scripts/scheduler/tests/ref_pack/*.json
    head -5 tmp/sched.csv

------------------------------------------------------------

## Simple sweeps

Sweep copies and chunk size (pack):

    copyspace-bench-core --bench pack --out tmp/pack_sweep.csv \
      --copies-list 32,64,128 \
      --chunk-bytes-list 32,64 \
      --src-stride-bytes-list 4096 \
      --repeat 1

Sweep modes and seeds (permute):

    copyspace-bench-core --bench permute --out tmp/permute_sweep.csv \
      --mode-list random \
      --seed-list 1,2,3 \
      --repeat 1

Sweep len and life (bulkcopy):

    copyspace-bench-core --bench bulkcopy --out tmp/bulk_sweep.csv \
      --len-bytes-list 16384,65536 \
      --life-list 20000 \
      --repeat 1

------------------------------------------------------------

## Summarize results (human-readable)

Create a summary report (markdown-like tables):

    python3 scripts/bench/summarize.py --in tmp/bench.csv > tmp/bench_summary.md
    sed -n '1,120p' tmp/bench_summary.md

------------------------------------------------------------

## The key metric

- vmrep_avg_bits_uniq_dst_per_tick:
  effective unique destination bits written per tick.
  This is a useful write throughput metric (overlapping writes do not inflate it).
