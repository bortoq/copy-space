# Audit v0 — stable interfaces and surfaces

Purpose
- This document inventories the stable, partner-facing interfaces and artifacts of copy-space.
- It is intended to reduce ambiguity about what is supported and what changes may require coordination.

Scope (v0)
- Scheduler v0 toolchain: solve, validate, pilot, bench.
- Contracts and documents used as source of truth.
- Environment variables used as interfaces (external solver hook, VM diagnostics and strict checks).

Out of scope (v0)
- Internal VM and Forth0 implementation details beyond what is needed to describe stable entrypoints.
- Full API stability guarantees for internal Python modules.

------------------------------------------------------------

## Stable user-facing CLI entrypoints

Defined in pyproject.toml [project.scripts].

- copyspace-validate
  - Purpose: validate a schedule against the STRICT1 model and produce a report with reproducible metrics.
  - Contract: doc/scheduler_io_v0.md and doc/strict1_model_v0.md

- copyspace-solve
  - Purpose: produce a schedule for a given instance using a selected solver strategy (baseline, greedy, external).
  - External solver hook (env-based): see Environment variables section.
  - Contract: doc/scheduler_io_v0.md

- copyspace-pilot
  - Purpose: a one-command helper for pilot workloads (CSV intake, solve, validate, artifacts emission).
  - Docs: doc/partners/quickstart_pilot.md

- copyspace-csv-to-instance
  - Purpose: convert pilot CSV into scheduler instance JSON.
  - Contract: doc/scheduler_io_v0.md

- copyspace-lines-to-schedule
  - Purpose: convert a schedule described as lines into scheduler schedule JSON.
  - Contract: doc/scheduler_io_v0.md

- copyspace-bench-scheduler
  - Purpose: run scheduler benchmark profiles and emit CSV reports (deterministic smoke and larger manual profiles).
  - Docs: doc/benchmarks.md, doc/bench_regression_policy.md

- copyspace-demo-scheduler
  - Purpose: run a small end-to-end demo flow for scheduler v0.
  - Docs: doc/quickstart.md

- copyspace-bench-core
  - Purpose: run core (non-scheduler) benchmark flows used for regression signals.
  - Docs: doc/benchmarks.md

Notes
- The CLI names above are considered stable surfaces.
- Exact flags and output fields are defined by the referenced contracts and help text; changes should be treated as compatibility-sensitive.

------------------------------------------------------------

## Contracts and schemas (source of truth)

Scheduler v0 I/O
- doc: doc/scheduler_io_v0.md
- Defines:
  - instance JSON shape
  - schedule JSON shape
  - validator report / metrics fields

STRICT1 model baseline
- doc: doc/strict1_model_v0.md
- Defines:
  - resource model and constraints used by validator and solvers

Partner-facing CI gate reference
- docs: doc/partners/ci_gate_recipe.md
- example workflow: doc/partners/ci_gate_workflow_example.yml

------------------------------------------------------------

## Artifacts and file formats

Scheduler v0 primary artifacts (as defined by contract)
- instance JSON
- schedule JSON
- validator report JSON

Bench artifacts
- Scheduler bench CSV and per-run JSON reports (see scripts and docs in doc/benchmarks.md).
- Bench regression policy: doc/bench_regression_policy.md

Pilot artifacts
- Output directories produced by copyspace-pilot may include:
  - instance JSON
  - schedule JSON
  - validator report JSON
  - optional HTML plots (if enabled)

Native tool artifacts
- GitHub Releases publish native tool archives for multiple platforms.
- Coverage and details live in CI workflows and release notes.

------------------------------------------------------------

## Environment variables (interfaces)

External solver integration (scheduler v0)
- COPYSPACE_INSTANCE_JSON
  - Set by: copyspace-solve when solver=external
  - Read by: external solver process
  - Meaning: absolute path to instance JSON file

- COPYSPACE_SCHEDULE_OUT
  - Set by: copyspace-solve when solver=external
  - Read by: external solver process
  - Meaning: absolute path where the external solver must write schedule JSON

- COPYSPACE_MODEL
  - Set by: copyspace-solve when solver=external
  - Meaning: model identifier used by the toolchain (STRICT1 baseline)

VM diagnostics and bench reporting (core benches)
- COPYSPACE_REPORT
- COPYSPACE_REPORT_FROM
- COPYSPACE_REPORT_LEN
- COPYSPACE_REPORT_HZ

VM strict runtime checks (opt-in)
- COPYSPACE_VM_STRICT_ALIGN32
  - Read by: vmrun
  - Meaning: enable strict pointer alignment and invariants (host-policy)

Partner CI example variable (not consumed by tools)
- COPYSPACE_REF
  - Used in: doc/partners/ci_gate_workflow_example.yml
  - Meaning: example of pinning a git ref in a partner CI workflow

------------------------------------------------------------

## CI and checks (coverage signals)

Primary CI workflow
- workflow: .github/workflows/ci.yml
- Includes:
  - make test, make tdd
  - scheduler tests: scripts/test_scheduler.sh
  - python packaging smoke: pip install -e . and CLI smoke
  - stress smoke: scripts/scheduler/stress_smoke.py (push main and manual)
  - bench smoke job (push main and manual)

Bench history publishing
- workflow: .github/workflows/bench_history_pages.yml

Extended benches (manual/nightly)
- workflow: .github/workflows/bench_extended.yml

Native build matrix (build-only)
- workflow: .github/workflows/ci.yml (native-build-matrix job)

------------------------------------------------------------

## Packaging and release surfaces

Package identity
- PyPI project: copy-space
- Source repository: https://github.com/bortoq/copy-space

Release process docs
- Release checklist: doc/release_checklist.md
- PyPI publish guide: doc/pypi_publish.md

------------------------------------------------------------

## Follow-ups

If a follow-up is accepted, it should be tracked only in doc/status.md, Next (prioritized).
Current known follow-ups include:
- CI: packaging sanity (build + twine check)
- PyPI: trusted publishing decision (OIDC)
