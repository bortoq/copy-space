# Audit report v0 — quality and alignment

Date: 2026-05-12
Scope: scheduler v0 toolchain, docs/contract alignment, CI signals, packaging and release surfaces.

This report is an actionable snapshot, not a long-term plan.
If follow-ups are accepted, they must be tracked only in doc/status.md, Next (prioritized).

------------------------------------------------------------

## Executive summary

Overall status: green for the scheduler v0 partner path, with a few clear follow-up candidates.

Strong points
- Partner-facing scheduler v0 flow has contracts and deterministic validation.
- CI covers core correctness (make test, make tdd) and scheduler v0 regression checks.
- Packaging quality improved: CI now builds sdist and wheel and runs twine check.
- Release 0.1.3 shipped to PyPI and has a GitHub Release.

Main risks / gaps (not yet tracked)
- No automated linting/formatting gate for Python and C (style drift can accumulate).
- No automated link checker for docs (broken links can slip in).
- Cross-platform CI runs Python-first smoke on macOS and Windows, but not full make test and make tdd there.

------------------------------------------------------------

## Evidence and reproducible checks

CI workflows (main branch)
- .github/workflows/ci.yml
  - build-and-test: make bins, make test, make tdd, scheduler tests, packaging smoke (editable install)
  - packaging-sanity: python -m build, python -m twine check dist/*
  - py-smoke-matrix: macOS and Windows Python-first smoke (installed entrypoints, pilot and small bench smoke)
  - stress-smoke: large-instance scheduler stress smoke (push main and manual)
  - bench-smoke: deterministic core bench smoke and scheduler unified bench smoke
  - native-build-matrix: CMake build-only on Linux, macOS, Windows
- .github/workflows/bench_history_pages.yml
- .github/workflows/bench_extended.yml

Release and publishing surfaces
- PyPI publish guide: doc/pypi_publish.md
- Trusted publishing workflow (OIDC): .github/workflows/publish_pypi.yml
- Release checklist: doc/release_checklist.md

Local checks typically used before push
  make test
  make tdd

------------------------------------------------------------

## Interface alignment review (docs vs code)

Stable entrypoints
- Inventory: doc/audit_v0.md
- Source of truth: pyproject.toml [project.scripts]
- Observed state: CLI names in audit inventory match pyproject scripts list.

Contracts and schemas
- Scheduler v0 I/O contract: doc/scheduler_io_v0.md
- STRICT1 baseline spec: doc/strict1_model_v0.md
- Partner CI gate docs: doc/partners/ci_gate_recipe.md and doc/partners/ci_gate_workflow_example.yml
- Observed state: docs point to contracts rather than duplicating schema details.

Environment variables (interfaces)
- External solver hook: COPYSPACE_INSTANCE_JSON, COPYSPACE_SCHEDULE_OUT, COPYSPACE_MODEL
- VM/bench reporting: COPYSPACE_REPORT, COPYSPACE_REPORT_FROM, COPYSPACE_REPORT_LEN, COPYSPACE_REPORT_HZ
- VM strict runtime checks (opt-in): COPYSPACE_VM_STRICT_ALIGN32
- Observed state: listed variables appear in code and/or docs; header guard false positives are excluded.

------------------------------------------------------------

## Packaging and release quality

Packaging sanity
- CI job packaging-sanity builds wheel and sdist and runs twine check, reducing the risk of broken long_description metadata and missing files.

Publishing security
- Token-based twine upload is documented.
- Trusted publishing path (OIDC) exists via publish_pypi.yml, but requires one-time configuration in PyPI trusted publishers.

Release alignment (0.1.3)
- Tag v0.1.3 exists.
- GitHub Release v0.1.3 exists.
- PyPI copy-space 0.1.3 exists.
- Sanity install check: pip install copy-space==0.1.3 and entrypoints help checks were performed during the 0.1.3 publish process.

------------------------------------------------------------

## Follow-up candidates (not tracked until accepted)

1) Docs: add a lightweight link checker or doc consistency checker in CI.
2) Python: add ruff (lint) in CI with a minimal rule set.
3) C: add a minimal formatting or linting signal, or at least a compilation warning policy.
4) Cross-platform: consider running a reduced make test on one non-Linux platform if runtime allows.

