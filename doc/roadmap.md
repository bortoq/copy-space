# Roadmap (public)

_file: doc/roadmap.md_

This roadmap matches the public partner-facing scope in `doc/partners/partner_brief.md`.
Focus: deterministic scheduling + independent validation + reproducible metrics for **directed full-mesh
transfer demands**, with two primary use cases:
- Pain C: benchmarking / regression tracking for scheduling strategies
- Pain A: CI gating for schedule correctness + performance regression prevention

---

## Milestone 0 — Engineering baseline (done)
Repository already includes:
- CI (`make bins`, `make test`, `make tdd`)
- Forth0-first regression tests executed via `forth0c`
- Benchmark sweeps and CSV reporting (`scripts/bench/run.sh`, `scripts/bench/summarize.py`)
- Core docs (semantics/testing/memory layout/etc.)

See: `doc/status.md`.

---

## Milestone 1 — MVP (validate + metrics + baseline scheduling)

### Scope (MVP)
- Input: directed demands `src_slot -> dst_slot` with `bits_total`
- Model: tick scheduling under **STRICT1** (each slot participates at most once per tick)
- Output: schedule + validator report + metrics report (CSV-friendly)

### Important clarification (addressing / memory allocation)
MVP is **volume-based**:
- the workload represents transfer volume between endpoints
- Copy-Space does **not** allocate or track address-level offsets inside slots

### Deliverables
1) Versioned I/O v0 (Instance + Schedule)
2) Hard validator (STRICT1 + bandwidth + coverage)
3) Validate-only workflow (accept externally produced schedules)
4) Two strategies: baseline + improved (no optimality claims)
5) End-to-end metrics (ticks/bits-per-tick/utilization + lower-bound reference)
6) Reference benchmark pack (public; seeded & reproducible)
7) CLI workflow (solve/validate/report)
8) **5-minute demo (real, committed)**
   - `scripts/scheduler/tests/demo_instance.json`
   - `python3 scripts/scheduler/demo_run.py`

### Definition of done (MVP)
- `./scripts/test_scheduler.sh` passes
- Reference pack benchmark runs and produces summary (baseline vs improved)
- Demo runner prints a real baseline vs improved delta (ticks_total/utilization)
- A partner can validate externally produced schedules (validate-only mode)

---

## Milestone 2 — CI gating + integration helpers (Pain A) and benchmarking UX (Pain C)
- Replace format previews with real CLI commands in `doc/partners/ci_gate_recipe.md`
- Add a minimal adapter: CSV `src_slot,dst_slot,bits_total` -> Instance v0
- Provide a “CI gate recipe” that compares `ticks_total`/`utilization` against a baseline artifact

---

## Non-goals (for now)
- No topology/path selection (full-mesh only)
- No address-level allocation/validation inside endpoints (`src_bit/dst_bit`)
- No “best price”/global optimality claims
