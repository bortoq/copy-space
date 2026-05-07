# Benchmark CSV schema (v0)

_file: doc/bench_csv_schema.md_

This document defines the **current v0** CSV schema emitted by benchmark wrappers and the demo.

Header source of truth:
- `python3 scripts/vmrep_to_csv.py --header`

---

## Versioning rules

- The schema is versioned (starting with **v0**).
- A breaking change must bump the version (v1, v2, ...).
- Non-breaking additions should append new columns at the end.

---

## Columns (exact order)

1) `schema_version` (currently `csv.v0`)
2) `bench`
3) `mode`
4) `seed`
5) `space_bytes`
6) `slots` (number of copy slots per tick; historically called `processor_n` in code/tools)
7) `addr_bits`
8) `ticks_total`
9) `moved_bits_total` (fallback: uses `vmrep_bits_sum_total` if not explicitly available)
10) `vmrep_bits_sum_total`
11) `vmrep_bits_uniq_dst_total`
12) `vmrep_avg_bits_sum_per_tick`
13) `vmrep_avg_bits_uniq_dst_per_tick`
14) `thr_from`
15) `thr_len`
16) `thr_avg_bits_sum_per_tick`
17) `thr_avg_bits_uniq_dst_per_tick`
18) `notes`
19) `git_rev`
20) `copies_total` (optional; set by wrappers if known)
21) `expected_bits_per_tick` (optional; set by wrappers if known)

