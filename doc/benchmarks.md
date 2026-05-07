# Benchmarks and Metrics

_file: doc/benchmarks.md_

This repo includes throughput benchmarks and a small reporting toolchain.

CSV schema reference:
- `bench_csv_schema.md`

## Benchmarks

- `pack`:
  compaction-like benchmark (sparse source -> dense destination).
  Useful mental model: "filter result compaction" in DB/analytics.

- `permute`:
  reorder-like benchmark (chunk permutation).
  Useful mental model: reorder/partition/materialization.

- `bulkcopy`:
  large contiguous copy per tick (upper bound style benchmark).

## Run benchmarks (CSV output)

Each benchmark wrapper prints one CSV row (no header):

- `scripts/bench_pack_csv.sh`
- `scripts/bench_permute_csv.sh`
- `scripts/bench_bulkcopy_csv.sh`

The demo script prints header + rows and saves to `tmp/demo.csv`:

    scripts/demo_db.sh > /dev/null 2> tmp/demo.stderr
    cat tmp/demo.csv

## The key metric

- `vmrep_avg_bits_uniq_dst_per_tick`:
  effective unique destination bits written per tick.
  This is a "useful write throughput" metric (overlapping writes do not inflate it).

