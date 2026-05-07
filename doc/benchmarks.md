# Benchmarks and Metrics

_file: doc/benchmarks.md_

This repo includes throughput benchmarks and a small reporting toolchain.

CSV schema (v0):
- `bench_csv_schema.md`
- header source of truth: `python3 scripts/vmrep_to_csv.py --header`

---

## Benchmarks

- `pack`:
  compaction-like benchmark (sparse source -> dense destination).
  Useful mental model: "filter result compaction" in DB/analytics.

- `permute`:
  reorder-like benchmark (chunk permutation).
  Useful mental model: reorder/partition/materialization.

- `bulkcopy`:
  large contiguous copy per tick (upper bound style benchmark).

---

## Run benchmarks

### Unified runner (recommended)

Run all benchmarks into one CSV file:

    scripts/bench/run.sh --bench all --out tmp/bench.csv
    head -5 tmp/bench.csv

Run just one:

    scripts/bench/run.sh --bench pack --out tmp/pack.csv

### Simple sweeps

Sweep copies and chunk size (pack):

    scripts/bench/run.sh --bench pack --out tmp/pack_sweep.csv \
      --copies-list 32,64,128 \
      --chunk-bytes-list 32,64 \
      --src-stride-bytes-list 4096 \
      --repeat 1

Sweep modes and seeds (permute):

    scripts/bench/run.sh --bench permute --out tmp/permute_sweep.csv \
      --mode-list random \
      --seed-list 1,2,3 \
      --repeat 1

Sweep len/life (bulkcopy):

    scripts/bench/run.sh --bench bulkcopy --out tmp/bulk_sweep.csv \
      --len-bytes-list 16384,65536 \
      --life-list 20000 \
      --repeat 1

---

## Summarize results (human-readable)

Create a summary report (markdown-like tables):

    python3 scripts/bench/summarize.py --in tmp/bench.csv > tmp/bench_summary.md
    sed -n '1,120p' tmp/bench_summary.md

---

## The key metric

- `vmrep_avg_bits_uniq_dst_per_tick`:
  effective unique destination bits written per tick.
  This is a "useful write throughput" metric (overlapping writes do not inflate it).

