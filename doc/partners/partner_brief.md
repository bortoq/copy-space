# Copy-Space — Partner brief (public)

Copy-Space is an open-source project for **validated scheduling** of transfer-style workloads.

**One-liner (partner-facing):**
> Provide transfer demands (`src_slot,dst_slot,bits_total`) and a resource model, and Copy-Space returns a
> conflict-free schedule, an independent validator report, and reproducible utilization metrics — suitable
> for benchmarking solver strategies and CI gating.

This document is intentionally non-sensitive and does not disclose solver internals.

---

## Two concrete pains we target (pilot-ready)

### Pain C — Scheduling strategy evaluation (benchmarking / regression tracking)
You already have a scheduler (or several heuristics), but you lack:
- a shared correctness gate,
- stable, comparable metrics across sweeps,
- and a way to track regressions over time.

**What Copy-Space provides:**
- a deterministic model + validator (objective correctness),
- a repeatable benchmark harness,
- standardized metrics (`ticks_total`, `bits_per_tick`, `utilization`) and summary tables.

### Pain A — CI gate for transfer schedules (conflicts and performance regressions)
You generate or modify schedules (or transfer plans) as part of firmware/toolchain/optimization work and you need:
- fail-fast detection of conflicts under a declared model,
- automated protection against performance regressions (e.g., longer schedules).

**What Copy-Space provides:**
- a hard validator you can run in CI,
- reproducible metrics you can threshold (e.g., “must not regress > X%”).

**What this replaces:**
- ad-hoc scripts, partial checks, and manual review of schedules that are hard to audit and easy to regress.

---

## Model (v0 baseline)
- Workload: directed full-mesh transfer demands `src_slot -> dst_slot` with `bits_total`.
- Output: a tick-based schedule consisting of per-tick transfer chunks.
- Resource model v0: STRICT1 — each slot participates at most once per tick (as src or dst).
- Bandwidth model: each tick has a configured maximum transfer chunk size.

### Important clarification: volume-based MVP
v0 focuses on conflicts, bandwidth, and time (ticks) for transfer volume.
It does NOT allocate or validate address-level src_bit/dst_bit offsets inside endpoints.

### Does STRICT1 fit you? (quick checklist)
STRICT1 is a good approximation if, per time step/tick, your system behaves like:
- each endpoint can participate in at most one transfer (either send or receive)
- you do not rely on broadcast/fanout within the same tick

If you need “1 read + 1 write per tick” or broadcast-style semantics, the model may need extension.

---

## Quick demo (real, runs end-to-end)
- Demo runner: `python3 scripts/scheduler/demo_run.py`
- Demo instance: `scripts/scheduler/tests/demo_instance.json`

The demo compares baseline vs improved scheduling on a fixed instance and prints
`ticks_total`, `utilization`, and the lower-bound reference.

- Optional visualizer (helps onboard quickly):
  - Run: `python -m streamlit run tools/visualizer/app.py`
  - Docs: `tools/visualizer/README.md`
