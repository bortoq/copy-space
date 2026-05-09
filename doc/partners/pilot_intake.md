# Pilot intake (v0)

This document describes what is needed to run a first pilot using Copy-Space v0 (STRICT1, volume-based, full-mesh).

## Goal of the pilot
- Validate schedules (correctness gate) and/or compare scheduling strategies with reproducible metrics.
- Produce a short report: ticks_total, utilization, and regression deltas vs baseline.

## What we need from you (minimal)
1) Demand list (preferred): CSV with columns:
   - src_slot,dst_slot,bits_total
   (header is recommended but not required)

2) Configuration:
   - slots (count), OR allow us to infer slots as max(slot_id)+1
   - copy_bw_bits_per_tick (integer > 0)

3) Acceptance criteria (pick a small set)
Examples:
- “Schedule must validate (no conflicts / exact coverage)”
- “ticks_total must not regress by more than X% vs baseline schedule”
- “utilization must be >= Y on our benchmark pack”

## Optional (helps a lot)
- Your current schedule output (any format), or your current heuristics’ result.
  We can convert it to Schedule v0 and validate/measure it.

## What you get back
- Validation report (PASS/FAIL) with reasons on failure.
- Metrics report (JSON): ticks_total, bits_total, bits_per_tick, utilization, lower-bound reference.
- Optional: schedules produced by Copy-Space strategies (baseline vs greedy) for comparison.

## Data handling
- Anonymized/synthetic data is acceptable.
- Slot naming can be kept private; only numeric IDs are required.
