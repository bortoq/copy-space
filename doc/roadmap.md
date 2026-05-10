# Roadmap (public)

_file: doc/roadmap.md_

This roadmap matches the public partner-facing scope in `doc/partners/partner_brief.md`.

Focus: deterministic scheduling + independent validation + reproducible metrics for **directed full-mesh**
transfer demands (volume-based), with two primary use cases:
- Pain C: benchmarking / regression tracking for scheduling strategies
- Pain A: CI gating for schedule correctness + performance regression prevention

See also: `doc/status.md`.

---

## Principles (accepted)

### Single source of truth
- Contracts and schemas live in `doc/*` (e.g. `doc/scheduler_io_v0.md`).
- README / partner docs should link to contracts rather than duplicate details.
- CI should include small smoke checks for canonical entrypoints and critical docs sync.

### Cross-platform direction
Goal: a user-facing workflow that does not rely on `/bin/sh` + coreutils.
Approach: Python entrypoints for orchestration; native binaries for VM/tools; portable native build + release artifacts.

### Bench in CI
Benchmarks should be runnable in automation in a deterministic smoke mode (small, fixed seeds).
If runtime becomes an issue, prefer nightly + manual trigger rather than removing coverage.

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
- Validator + metrics (coverage required by default): `copyspace-validate`
- Two strategies (baseline + greedy): `copyspace-solve`
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
- CSV -> Instance adapter: `copyspace-csv-to-instance`
- One-command pilot runner:
  - `scripts/scheduler/pilot_run.sh`
  - example input: `examples/demands.csv`
- Validate-only helper (text lines -> Schedule v0):
  - `copyspace-lines-to-schedule`
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
4) Public docs hygiene:
   - clarify canonical entrypoints (`copyspace-*`) vs internal scripts
   - keep contracts in `doc/*` as the source of truth

---

## Milestone 4 — Cross-platform UX + portable native build (next)

Goal: a user can run core workflows on Linux/macOS/Windows without requiring `/bin/sh`.

Deliverables:
1) Portable native build (in parallel to Makefile):
   - add CMake build for native tools (`vmrun`, `mkimage_std7_fixed`, `forth0c`, `vmprep_forth0`, etc.)
2) CI: native build matrix (build-only initially):
   - `ubuntu-latest`, `macos-latest`, `windows-latest`
3) Prebuilt binaries:
   - produce release artifacts for native tools per platform (GitHub Releases)
4) Python-first orchestration:
   - add/extend Python entrypoints to cover user-facing flows (bench/pilot/demo) without shell scripts
   - ensure docs do not require `./scripts/*.sh` for baseline usage

---

## Milestone 5 — Bench CI + performance regression signals (next)

Goal: deterministic, automated signals for bench-level regressions.

Deliverables:
1) CI: add a deterministic bench smoke job:
   - minimal sweep; fixed seeds; bounded runtime
2) Optional: nightly extended benches:
   - larger sweeps / reference pack tracking

---

## Milestone 6 — Scheduler scalability (long-term)

Goal: handle instances with large `bits_total` without memory blowups.

Deliverables:
- Avoid expanding demands into per-bw chunks in the host solver:
  - represent pending as `(src, dst, remaining_bits)` and emit chunks on demand
- Add reproducible stress fixtures + metrics for large instances

---

## Non-goals (current scope)
- No topology/path selection (full-mesh only)
- No address-level allocation/validation inside endpoints (`src_bit/dst_bit`)
- No global optimality claims
