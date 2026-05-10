# Status — std7_fixed + forth0 + scheduler v0 — 2026-05-09

_file: doc/status.md_

This is a **status/progress** document (what is done and how it is tested), not a long-term plan.
For plans: `doc/roadmap.md`.

Legend:
- `[x]` done (with stable tests / usage)
- `[~]` partial / could be improved
- `[ ]` not done / deferred

---

## Where tests live

- Forth0 libs: `src/forth0/lib/`
- Forth0 tests: `src/forth0/tests/`
- TDD harness scripts: `scripts/tdd/test_forth0*.sh`
- Main regression harness: `scripts/test_all.sh`
- Runner: `scripts/tdd/run_all.sh`

Scheduler v0 (Python tooling):
- Scheduler smoke/regression test: `./scripts/test_scheduler.sh`
- Scheduler fixtures: `scripts/scheduler/tests/`
- Scheduler demo: `python3 scripts/scheduler/demo_run.py`

---

## A) Engineering baseline

- [x] `VM_ERR` diagnostics covered by TDD:
  - `scripts/tdd/test_vmerr_diag.sh`

- [x] Standardized test scratch:
  - policy: `ART_TESTG == ART_TESTSCR_BASE`
  - `ART_TESTSCR_BASE/ART_TESTSCR_END` (ART[63..64])
  - TDD:
    - `scripts/tdd/test_scratch_abi.sh`
    - `scripts/tdd/test_scratch_artifacts.sh`

- [x] TERM0 descriptor ABI (devices/bus baseline):
  - TDD: `scripts/tdd/test_term0_desc_abi.sh`
  - doc: `doc/devices.md`

- [x] Fail bundles:
  - TDD: `scripts/tdd/test_fail_bundle.sh`
  - fail bundles produced by: `scripts/test_all.sh` → `tmp/fail/...`

- [x] vmrep tooling selftest:
  - TDD: `scripts/tdd/test_vmrep_tools.sh`

- [x] ABI artifacts doc sync:
  - TDD: `scripts/tdd/test_art_doc_sync.sh`
  - doc: `doc/abi_artifacts.md`

- [x] CI:
  - `.github/workflows/ci.yml` (make bins / make test / make tdd / ABI doc sync / scheduler v0 tests)

---

## B) 2b pointers (block pointers)

### Base ptr words / primitives
- [x] `LITAP/LITBP/LITRP`, `VAR_AP/VAR_BP/VAR_RP` (ART[55..60])
- [x] `LOAD24AP/LOAD24BP/STORE24RP` (ART[67..69])
- [x] Padding semantics:
  - Forth0 test: `src/forth0/tests/test_ptrprims_padding.f0`
  - TDD: `scripts/tdd/test_forth0_ptrprims.sh`

### Derived pointer arithmetic (no new ART)
- [x] `INC_PTR32` (derived):
  - Forth0 test: `src/forth0/tests/test_incptr32.f0`
  - TDD: `scripts/tdd/test_forth0_ptr32.sh`
- [x] `ADD_PTR_CONST32` (derived):
  - Forth0 test: `src/forth0/tests/test_addptr_const32.f0`
  - TDD: `scripts/tdd/test_forth0_ptr32.sh`
### Derived pointer-based ops (via primitives)
- [x] `ADD24P` via prims:
  - Forth0 test: `src/forth0/tests/test_add24p_via_prims.f0`
  - TDD: `scripts/tdd/test_forth0_add24p.sh`
- [x] `LT24P` via prims:
  - Forth0 test: `src/forth0/tests/test_lt24p_via_prims.f0`
  - TDD: `scripts/tdd/test_forth0_lt24p.sh`
- [x] `EQ24P` test:
  - Forth0 test: `src/forth0/tests/test_eq24p.f0`
  - TDD: `scripts/tdd/test_forth0_ptrprims.sh`

### Alignment contract
- [x] Optional strict host-side check:
  - `F0C_STRICT_ALIGN32=1`
  - negative TDD: `scripts/tdd/test_forth0c_strict.sh`
- [ ] VM runtime checks (not required for baseline)

### Deferred
- [ ] Raw bit pointers / bit pointers (not required for block-pointer baseline)

---

## Forth0-first baseline

- [x] Host compiler: `build/bin/forth0c` (implementation: `src/forth0/host/`)
- [x] Execution pipeline documented:
  - `doc/forth0.md`
  - `doc/testing.md`
- [x] `make test` and `make tdd` run `.f0` tests (forth0-first)
- [x] Legacy C token-generators are optional:
  - `make tok`
  - `make TOK=1 bins`

---

## 2a arithmetic (baseline)

- [x] Forth0 tests:
  - `src/forth0/tests/test_add24.f0`
  - `src/forth0/tests/test_eq24.f0`
  - `src/forth0/tests/test_lt24.f0`
  - TDD: `scripts/tdd/test_forth0_2a.sh`

- [x] Bit-level regression tests (Forth0):
  - `src/forth0/tests/test_fulladder.f0`
  - `src/forth0/tests/test_add8.f0`
  - TDD: `scripts/tdd/test_forth0_bitops.sh`

---

## Copy-space scheduler v0 (volume-based, STRICT1)

### Contract / docs
- [x] v0 I/O + validation + metrics contract:
  - `doc/scheduler_io_v0.md`
- [x] Public roadmap and partner-facing docs (non-sensitive):
  - `doc/roadmap.md`
  - `doc/partners/partner_brief.md`
  - `doc/partners/pilot_intake.md`
  - `doc/partners/quickstart_pilot.md`
  - `doc/partners/ci_gate_recipe.md`
  - `doc/partners/pilot_report_example.md`

### Tools (Python, v0)
- [x] Python package + CLI entrypoints (optional):
  - `pyproject.toml`
  - entrypoints: `copyspace-validate`, `copyspace-solve`, `copyspace-pilot`
  - recommended install: `python3 -m venv .venv && . .venv/bin/activate && python -m pip install -e .`

- [x] Validate schedule (STRICT1 + bandwidth + coverage):
  - `scripts/scheduler/validate_v0.py`
  - exit codes: 0 PASS, 2 FAIL, 1 parse/usage
  - supports `--report report.json` and `--quiet`
- [x] Solve instance (two strategies):
  - `scripts/scheduler/solve_v0.py --solver baseline|greedy`
- [x] CSV demands -> Instance v0:
  - `scripts/scheduler/csv_to_instance_v0.py`

- [x] Optional Streamlit visualizer (onboarding / schedule timeline view):
  - `python -m streamlit run tools/visualizer/app.py`
  - doc: `tools/visualizer/README.md`

### Next (prioritized)
- [x] CI: validate Python packaging + CLI entrypoints (installed mode):
  - update: `.github/workflows/ci.yml`
  - add steps: `python -m pip install -e .` and a smoke run of `copyspace-*` (e.g. solve demo instance -> validate)
  - goal: CI catches broken entrypoints/imports even if scripts/ are still runnable

- [x] Bench harness: remove dependency on executable-bit for Python generators:
  - update bench scripts to call generators explicitly via `python3 scripts/mkbench_*.py ...`
  - goal: avoid `exit=126`/permission issues on fresh checkouts / different filesystems

- [ ] Bench diagnostics: improve error visibility on non-zero exit:
  - ensure bench scripts print failing command and tail relevant logs on error
  - consider `--verbose/--keep-tmp` flags for easier reproduction

- [ ] Packaging: declare optional dependencies for visualizer:
  - update: `pyproject.toml` (`[project.optional-dependencies]`, e.g. `viz = ["streamlit>=..."]`)
  - goal: `pip install -e ".[viz]"` enables visualizer deterministically

- [ ] Scheduler scalability (long-term): avoid expanding demands into per-bw chunks for very large instances:
  - consider representing pending as `(src, dst, remaining_bits)` and emitting chunks on demand
  - goal: reduce memory/time blowups on large `bits_total`

### Demo / reference pack
- [x] Real demo instance + runner:
  - `scripts/scheduler/tests/demo_instance.json`
  - `python3 scripts/scheduler/demo_run.py`
- [x] Seeded public reference pack generator + benchmark:
  - `scripts/scheduler/gen_ref_pack.py`
  - `scripts/scheduler/bench_v0.py`
### Bench harness integration (unified CSV schema v0)
- [x] Scheduler results can be appended into unified CSV v0:
  - row generator: `scripts/scheduler/sched_to_csv_row_v0.py`
  - wrapper: `scripts/bench_scheduler_csv.sh`
  - unified runner: `scripts/bench/run.sh --bench scheduler ...`
    - supports `--solver-list` and `--inst-glob`
- [x] Summarization works with existing tool:
  - `python3 scripts/bench/summarize.py --in tmp/sched.csv`

### How to run (quick)
- Scheduler tests:
  - `./scripts/test_scheduler.sh`
- Demo:
  - `python3 scripts/scheduler/demo_run.py`
- Reference pack:
  - `python3 scripts/scheduler/gen_ref_pack.py`
  - `python3 scripts/scheduler/bench_v0.py | tail -n 40`
- Unified bench:
  - `scripts/bench/run.sh --bench scheduler --out tmp/sched.csv --repeat 1`
  - `scripts/bench/run.sh --bench scheduler --out tmp/sched_pack.csv --inst-glob scripts/scheduler/tests/ref_pack/*.json --solver-list baseline greedy --repeat 1`

### CI
- [x] Scheduler tests run in CI:
  - `./scripts/test_scheduler.sh`

---

## Licensing
- [x] Project license: Apache-2.0
  - `LICENSE`, `NOTICE`
