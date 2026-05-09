# Example pilot report (public, format preview)

This is a **format preview** of what a partner-facing report can look like once Milestone 1 CLI is in place.
Numbers below are illustrative; the goal is to show *fields and artifacts*, not to claim current results.

---

## 1) Input (partner provides)

Demands (CSV):
src_slot,dst_slot,bits_total
0,1,4096
0,2,2048
3,4,4096
2,5,1024

Configuration:
- slots = 6
- copy_bw_bits_per_tick = 256
- resource model: STRICT1

---

## 2) Output artifacts (Copy-Space produces)

Schedule artifact:
- a schedule is a list of ticks
- each tick contains a set of transfer chunks:
  - `src_slot, dst_slot, len_bits`

Validator report (CI-friendly):
VALIDATION: PASS
model: STRICT1
ticks_total: 42

(On failure):
VALIDATION: FAIL
reason: STRICT1 conflict
tick: 7
slot: 2

Metrics report:
ticks_total: 42
bits_total: 9216
bits_per_tick: 219.43
expected_bits_per_tick: 768
utilization: 0.2857
max_degree_chunks: 40

---

## 3) Baseline vs improved
Comparative table on a benchmark pack:
instance | solver   | ticks_total | utilization
ex-001   | baseline | 42          | 0.29
ex-001   | improved | 36          | 0.34
