# Roadmap (public)

_file: doc/roadmap.md_

This roadmap matches the public partner-facing scope in `doc/partners/partner_brief.md`.

Focus: deterministic scheduling + independent validation + reproducible metrics for **directed full-mesh**
transfer demands (volume-based), with two primary use cases:
- Pain C: benchmarking / regression tracking for scheduling strategies
- Pain A: CI gating for schedule correctness + performance regression prevention

See also: `doc/status.md`.

---

## Milestone 0 — Engineering baseline (done)
- CI (`make bins`, `make test`, `make tdd`)
- Forth0-first regression tests executed via `forth0c`
- Benchmark sweeps and CSV reporting (`scripts/bench/run.sh`, `scripts/bench/summarize.py`)
- Core docs (semantics/testing/memory layout/etc.)

---

## Milestone 1 — MVP: validated scheduling v0 (done)

### Scope
- Input: directed demands `src_slot -> dst_slot` with `bits_total`
- Model: tick scheduling under **STRICT1** (each slot participates at most once per tick)
- Output: schedule + validator report + reproducible metrics

### Key implementation artifacts
- I/O v0 contract: `doc/scheduler_io_v0.md`
- Validator + metrics (coverage required by default): `scripts/scheduler/validate_v0.py`
- Two strategies (baseline + greedy): `scripts/scheduler/solve_v0.py`
- Reference benchmark pack (seeded): `scripts/scheduler/gen_ref_pack.py`, `scripts/scheduler/bench_v0.py`
- Real demo:
  - instance: `scripts/scheduler/tests/demo_instance.json`
  - runner: `python3 scripts/scheduler/demo_run.py`
- Unified CSV harness integration (scheduler is a first-class bench):
  - `scripts/bench/run.sh --bench scheduler`
  - `scripts/bench/summarize.py`

### Definition of done (met)
- `./scripts/test_scheduler.sh` passes
- demo shows a real baseline vs greedy delta
- reference pack benchmark shows greedy is never worse and sometimes better

---

## Milestone 2 — CI gating + pilot helpers (done)

- Real CI gate recipe (incl. `--quiet`): `doc/partners/ci_gate_recipe.md`
- CSV -> Instance adapter: `scripts/scheduler/csv_to_instance_v0.py`
- One-command pilot runner:
  - `scripts/scheduler/pilot_run.sh`
  - example input: `examples/demands.csv`
- Validate-only helper (text lines -> Schedule v0):
  - `scripts/scheduler/lines_to_schedule_v0.py`
- Pilot path docs:
  - `doc/partners/pilot_intake.md`
  - `doc/partners/quickstart_pilot.md`

---

## Milestone 3 — Release + repo hygiene (next)

Goal: make it easy to reference a stable version and to accept contributions/pilot requests.

Deliverables:
1) Tag and publish **v0.1.0** (GitHub Release with short notes and quickstart commands).
2) GitHub issue templates:
   - Pilot request (collect workload shape and constraints)
   - Bug report (collect instance/schedule + validator report)
3) CONTRIBUTING.md (how to run tests/benches, where to put new instances, PR checklist).
4) Optional packaging:
   - Python CLI entrypoints (`copyspace-solve`, `copyspace-validate`, `copyspace-pilot`)
   - Keep scripts as source of truth; entrypoints are thin wrappers.

---

## Non-goals (current scope)
- No topology/path selection (full-mesh only)
- No address-level allocation/validation inside endpoints (`src_bit/dst_bit`)
- No “best price”/global optimality claims
