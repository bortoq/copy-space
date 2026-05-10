---
name: Pilot request (validated scheduling)
about: Request a small pilot / evaluation run (STRICT1, volume-based)
title: "[pilot] <short title>"
labels: ["pilot"]
assignees: []
---

## What you want to validate / measure
(One sentence. E.g. CI gating for schedule regressions, comparing heuristics, etc.)

## Data you can provide
- [ ] Demands CSV/JSON: src_slot,dst_slot,bits_total
- [ ] Existing schedule (validate-only)
- [ ] Anonymized/synthetic is OK

Attach files or link to a gist/private share and describe how to access.

## Model / constraints (v0)
- slots: <number> (or "infer from max slot id + 1")
- copy_bw_bits_per_tick: <number>
- STRICT1 fit:
  - [ ] each endpoint participates at most once per tick (send or receive)
  - [ ] no broadcast/fanout within a tick
  - If unsure, describe briefly.

## Acceptance criteria
Examples:
- schedule must validate (PASS)
- ticks_total must not regress more than X%
- utilization must be >= Y

## Notes
Anything else: scale (approx rows), runtime constraints, what "slot" represents, etc.
