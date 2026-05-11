---
name: Pilot request (validated scheduling)
about: Request a small pilot / evaluation run (STRICT1, volume-based)
title: "[pilot] <short title>"
labels: ["pilot"]
assignees: []
---

Start here (what we will ask for anyway):
- doc/partners/pilot_intake.md
- doc/partners/quickstart_pilot.md

## Goal
What do you want to validate or measure?
Examples:
- CI gating: schedule correctness plus non-regression limits vs a baseline
- Compare scheduling strategies (your scheduler vs Copy-Space baseline/greedy)
- Validator-only adoption (you generate schedules, we validate and report metrics)

## Data you can provide
Preferred:
- demands CSV with columns: src_slot,dst_slot,bits_total

Optional:
- existing schedule (any format) + a short description
- anonymized or synthetic data is OK

Attach files, or link to a private share and describe access.

## Model / constraints (v0, STRICT1)
- slots: <number> (or "infer from max slot id + 1")
- copy_bw_bits_per_tick: <integer>

STRICT1 constraints (quick check):
- each slot participates at most once per tick (as src or dst)
- no multi-destination fanout within a tick

If unsure, describe your constraints and we will map them to the model.

## Acceptance criteria (CI gate style)
Pick a small set. Examples:
- Must validate: copyspace-validate returns PASS
- ticks_total must not regress more than X percent vs baseline schedule
- utilization must be at least Y on your pack
- gap_to_lower_bound must not regress more than Z

## Notes
Scale expectations (number of rows, typical bits_total), runtime constraints,
what a slot represents, and what output artifacts you want back (reports only vs full schedules).
