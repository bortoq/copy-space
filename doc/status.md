# Status — std7_fixed + forth0 + scheduler v0 — 2026-05-12
#
# File: doc/status.md
#
# This is a status/progress document: what is done and how it is tested.
# For plans: doc/roadmap.md

Legend:
- [x] done (stable tests / usage)
- [~] partial / could be improved
- [ ] not done / deferred

References:
- Quickstart: doc/quickstart.md
- Testing guide: doc/testing.md
- Scheduler v0 contract: doc/scheduler_io_v0.md
- STRICT1 baseline spec: doc/strict1_model_v0.md
- Cross-platform guide: doc/cross_platform.md
- Release checklist: doc/release_checklist.md

------------------------------------------------------------

## Next (prioritized)

------------------------------------------------------------

## Recently completed (2026-05)

- [x] Milestone 8: Audit report v0 (quality and alignment)
  - doc: doc/audit_report_v0.md

- [x] PyPI: trusted publishing decision (OIDC) and workflow path
  - workflow: .github/workflows/publish_pypi.yml
  - doc: doc/pypi_publish.md
  - Note: requires one-time PyPI trusted publisher configuration for bortoq/copy-space

- [x] CI: packaging sanity (build + twine check)
  - CI job: packaging-sanity in .github/workflows/ci.yml

- [x] Milestone 7: Audit v0 doc (stable interfaces and surfaces)
  - doc: doc/audit_v0.md

- [x] Release 0.1.3: PyPI publish + GitHub Release
  - PyPI: https://pypi.org/project/copy-space/0.1.3/
  - GitHub Release: https://github.com/bortoq/copy-space/releases/tag/v0.1.3
  - Sanity: pip install copy-space==0.1.3; entrypoints copyspace-validate/copyspace-solve/copyspace-pilot --help

- [x] Documentation hygiene and clear product positioning
  - Clarified Scheduler v0 as the primary pilot-facing product
  - Split "pilot path" and "under the hood (VM/Forth0)" in README.md, overview.md, doc/README.md and roadmap.md
  - Removed conflicting language and outdated milestones
  - Covered by: doc/status.md, doc/roadmap.md, README.md

- [x] Docs: benchmarks and quickstart recommend python-first bench entrypoints
  - Updated: doc/benchmarks.md, doc/quickstart.md

- [x] Examples: ring15 pilot hero demo
  - files: examples/ring15.csv, examples/README.md
  - run: copyspace-pilot --csv examples/ring15.csv --bw 256 --outdir tmp/pilot_ring15 --plot

- [x] Bench regression policy (v0)
  - doc: doc/bench_regression_policy.md
  - Covered by: bench-smoke job in .github/workflows/ci.yml; bench history workflow .github/workflows/bench_history_pages.yml

- [x] Extended benches (manual/nightly)
  - workflow: .github/workflows/bench_extended.yml (workflow_dispatch + weekly schedule)
  - artifacts: bench-extended-core, bench-extended-scheduler

- [x] VM core decoupling v1: vmrep via VM hooks; invariants moved to host-policy
  - Updated: src/vm/space.h, src/vm/space.c, src/vm/diag/vmrep_attach.*, src/tools/vmrun.c
  - Covered by: make test, make tdd; CI main workflow

- [x] VM runtime checks (opt-in): pointer alignment and invariants (host-policy)
  - Enabled via: COPYSPACE_VM_STRICT_ALIGN32=1 (vmrun)
  - Checks:
    - 32-bit alignment (VAR_AP/VAR_BP/VAR_RP)
    - bounds (min_bits=24 for LOAD24/STORE24 style access)
    - processor/MMIO region rejection (null=0 allowed)
    - VAR_RP protected-region rejection (keeps RP away from ART and VAR tables)
  - Tests: scripts/tdd/test_vmrun_strict_align32.sh (bad_mmio_ptr.f0, bad_oob_ptr.f0, bad_rp_protected_ptr.f0)
  - Code: src/tools/vmrun.c, src/vm/invariants.c

- [x] Repo hygiene: python-first benches in Pages workflow and dev tooling; PR template
  - Updated: .github/workflows/bench_history_pages.yml, scripts/prepush_check.sh, scripts/bench/plot_scheduler_pack.py, CONTRIBUTING.md, .github/pull_request_template.md
  - Covered by: CI job bench-smoke in .github/workflows/ci.yml; Pages workflow bench_history_pages.yml

- [x] Cross-platform UX: python-first smoke flows covered on macOS and Windows in CI
  - CI job: py-smoke-matrix in .github/workflows/ci.yml (macos-latest, windows-latest)

- [x] Scheduler scalability stress smoke coverage (large-instance regression signal)
  - runner: scripts/scheduler/stress_smoke.py
  - CI job: stress-smoke in .github/workflows/ci.yml (push main and workflow_dispatch; skipped on pull_request)
  - profile: slots=16 bw=256 bits_per_pair=65536 pattern=full-mesh; solvers baseline and greedy
  - artifacts: instance.json, report_*.json, summary.json (schedule JSON deleted by default)

- [x] Live CI gate recipe (copy-paste workflow example for partners)
  - docs: doc/partners/ci_gate_recipe.md
  - workflow example: doc/partners/ci_gate_workflow_example.yml

- [x] Cross-platform: portable native build and distribution
  - CMake build: CMakeLists.txt
  - CI matrix build-only: native-build-matrix job in .github/workflows/ci.yml
  - native tool release artifacts: .github/workflows/release_native_tools.yml

- [x] Benchmark history
  - GitHub Pages: https://bortoq.github.io/copy-space/
  - workflow: .github/workflows/bench_history_pages.yml

- [x] External solver integration hook
  - solver mode: copyspace-solve --solver external
  - external interface: env COPYSPACE_INSTANCE_JSON and COPYSPACE_SCHEDULE_OUT

- [x] External solver reporting in scheduler bench CSV
  - scheduler bench CSV supports solver=external (notes include solver=external)

- [x] Pilot artifacts: optional HTML plots for onboarding
  - copyspace-pilot supports --plot to emit plot_baseline.html and plot_greedy.html

- [x] Release checklist (prevent version and doc drift)
  - doc/release_checklist.md

- [x] Docs: PyPI publishing guide
  - doc: doc/pypi_publish.md
  - Linked from: doc/release_checklist.md

- [x] CI bench smoke job
  - job: bench-smoke in .github/workflows/ci.yml
  - behavior: runs on push and workflow_dispatch; skipped on pull_request (verified via gh)

------------------------------------------------------------

## A) Engineering baseline

- [x] VM_ERR diagnostics covered by TDD
  - test: scripts/tdd/test_vmerr_diag.sh

- [x] Standardized test scratch
  - policy: ART_TESTG equals ART_TESTSCR_BASE
  - tests:
    - scripts/tdd/test_scratch_abi.sh
    - scripts/tdd/test_scratch_artifacts.sh

- [x] TERM0 descriptor ABI (devices/bus baseline)
  - test: scripts/tdd/test_term0_desc_abi.sh
  - doc: doc/devices.md

- [x] Fail bundles
  - test: scripts/tdd/test_fail_bundle.sh
  - produced by: scripts/test_all.sh -> tmp/fail

- [x] vmrep tooling selftest
  - test: scripts/tdd/test_vmrep_tools.sh

- [x] ABI artifacts doc sync
  - test: scripts/tdd/test_art_doc_sync.sh
  - doc: doc/abi_artifacts.md

- [x] CI (GitHub Actions)
  - main CI: .github/workflows/ci.yml
    - build: make bins
    - tests: make test, make tdd
    - scheduler tests: scripts/test_scheduler.sh
    - packaging smoke: pip install -e . and copyspace-* smoke
    - bench smoke (push and manual): bench-smoke job
    - python-first core benches smoke: copyspace-bench-core (pack/permute/bulkcopy)
    - CMake native build matrix: native-build-matrix job (linux, macos, windows)
  - native tool release artifacts: .github/workflows/release_native_tools.yml
  - bench history publishing: .github/workflows/bench_history_pages.yml

------------------------------------------------------------

## B) 2b pointers (block pointers)

Base ptr words / primitives:
- [x] LITAP/LITBP/LITRP and VAR_AP/VAR_BP/VAR_RP (ART 55..60)
- [x] LOAD24AP/LOAD24BP/STORE24RP (ART 67..69)
- [x] Padding semantics
  - Forth0 test: src/forth0/tests/test_ptrprims_padding.f0
  - TDD: scripts/tdd/test_forth0_ptrprims.sh

Derived pointer arithmetic (no new ART):
- [x] INC_PTR32
  - Forth0 test: src/forth0/tests/test_incptr32.f0
  - TDD: scripts/tdd/test_forth0_ptr32.sh
- [x] ADD_PTR_CONST32
  - Forth0 test: src/forth0/tests/test_addptr_const32.f0
  - TDD: scripts/tdd/test_forth0_ptr32.sh

Derived pointer-based ops (via primitives):
- [x] ADD24P via prims
  - Forth0 test: src/forth0/tests/test_add24p_via_prims.f0
  - TDD: scripts/tdd/test_forth0_add24p.sh
- [x] LT24P via prims
  - Forth0 test: src/forth0/tests/test_lt24p_via_prims.f0
  - TDD: scripts/tdd/test_forth0_lt24p.sh
- [x] EQ24P test
  - Forth0 test: src/forth0/tests/test_eq24p.f0
  - TDD: scripts/tdd/test_forth0_ptrprims.sh

Alignment contract:
- [x] Optional strict host-side check (forth0c)
  - env: F0C_STRICT_ALIGN32=1
  - negative TDD: scripts/tdd/test_forth0c_strict.sh
- [ ] VM runtime alignment checks are deferred (tracked in Next)

------------------------------------------------------------

## Forth0-first baseline

- [x] Host compiler: build/bin/forth0c
  - implementation: src/forth0/host
- [x] Execution pipeline documented
  - doc/forth0.md
  - doc/testing.md
- [x] make test and make tdd run Forth0 tests

Legacy C token-generators:
- [x] Optional (not required for baseline)
  - make tok
  - make TOK=1 bins

------------------------------------------------------------

## 2a arithmetic (baseline)

- [x] Forth0 tests
  - src/forth0/tests/test_add24.f0
  - src/forth0/tests/test_eq24.f0
  - src/forth0/tests/test_lt24.f0
  - TDD: scripts/tdd/test_forth0_2a.sh

- [x] Bit-level regression tests (Forth0)
  - src/forth0/tests/test_fulladder.f0
  - src/forth0/tests/test_add8.f0
  - TDD: scripts/tdd/test_forth0_bitops.sh

------------------------------------------------------------

## Copy-space scheduler v0 (volume-based, STRICT1)

Contract and model docs (source of truth):
- [x] Scheduler I/O v0 contract: doc/scheduler_io_v0.md
- [x] STRICT1 model spec (one-page): doc/strict1_model_v0.md

Partner-facing docs (public, non-sensitive):
- [x] doc/partners/partner_brief.md
- [x] doc/partners/pilot_intake.md
- [x] doc/partners/quickstart_pilot.md
- [x] doc/partners/ci_gate_recipe.md
- [x] doc/partners/pilot_report_example.md

Tools (Python, v0):
- [x] Python package and CLI entrypoints
  - config: pyproject.toml
  - entrypoints: copyspace-validate, copyspace-solve, copyspace-pilot, copyspace-csv-to-instance, copyspace-lines-to-schedule
  - demo entrypoint: copyspace-demo-scheduler (scripts/scheduler/demo_run.py is a thin wrapper)
  - pilot runner: copyspace-pilot (scripts/scheduler/pilot_run.sh is a thin wrapper)
  - core dependencies: none (dependencies is empty)

- [x] Validate schedule (STRICT1 + bandwidth + coverage) + metrics
  - entrypoint: copyspace-validate
  - wrapper: scripts/scheduler/validate_v0.py
  - exit codes: 0 PASS, 2 FAIL, 1 parse/usage
  - reports include lower bound and gap metrics:
    - lower_bound_ticks, gap_ticks, gap_to_lower_bound
  - covered by: scripts/test_scheduler.sh

- [x] Solve instance (baseline, greedy, external)
  - entrypoint: copyspace-solve
  - wrapper: scripts/scheduler/solve_v0.py
  - external solver mode: solver=external with env interface
  - covered by: scripts/test_scheduler.sh

- [x] CSV demands to instance v0
  - entrypoint: copyspace-csv-to-instance
  - wrapper: scripts/scheduler/csv_to_instance_v0.py

- [x] Text lines to schedule v0
  - entrypoint: copyspace-lines-to-schedule
  - wrapper: scripts/scheduler/lines_to_schedule_v0.py

Visualizer (optional):
- [x] Streamlit visualizer for onboarding and schedule timeline view
  - run: python -m streamlit run tools/visualizer/app.py
  - doc: tools/visualizer/README.md
  - install extras: pip install -e .[viz]

Testing:
- [x] Scheduler validator and solver tests
  - script: scripts/test_scheduler.sh
  - fixtures: scripts/scheduler/tests
  - includes adversarial and edge-case instances:
    - edge_2slots.instance.json
    - edge_2slots_dupdemands.instance.json
    - adv_star_8.instance.json
    - adv_cycle_8.instance.json

Bench integration (unified CSV schema v0):
- [x] Scheduler results can be appended into unified CSV v0
  - row generator: scripts/scheduler/sched_to_csv_row_v0.py
  - wrapper: scripts/bench_scheduler_csv.sh
  - python entrypoint: copyspace-bench-scheduler
  - python-first runner: copyspace-bench-scheduler
  - scheduler bench notes include:
    - solver, lb, gap, gap_ratio

------------------------------------------------------------

## Licensing

- [x] Apache-2.0
  - LICENSE, NOTICE
- [x] Third-party notes
  - THIRD_PARTY.md
