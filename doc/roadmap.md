# Roadmap (public)

_file: doc/roadmap.md_

This roadmap matches the public partner-facing scope in doc/partners/partner_brief.md.

Focus: validated scheduling plus independent validation and reproducible metrics for directed transfer demands
(volume-based) under the STRICT1 resource model.

Primary user-facing use cases:
- CI gating for schedule correctness plus performance regression limits
- Benchmarking and regression tracking for scheduling strategies

See also: doc/status.md

------------------------------------------------------------

## Principles (accepted)

Single source of truth
- Contracts and schemas live in doc (for example doc/scheduler_io_v0.md).
- README and partner docs should link to contracts rather than duplicating details.
- CI should include small smoke checks for canonical entrypoints and critical doc sync.

Cross-platform direction
Goal: user-facing workflows should not rely on /bin/sh plus coreutils.
Approach: Python entrypoints for orchestration; native binaries for VM tools; portable native build and release artifacts.

Bench in CI
Benchmarks should be runnable in automation in a deterministic smoke mode (small, fixed seeds).
If runtime becomes an issue, prefer nightly plus manual trigger rather than removing coverage.

------------------------------------------------------------

## Milestone 0 — Engineering baseline (done)

- CI: make bins, make test, make tdd
- Forth0-first regression tests executed via forth0c
- Core docs (semantics, testing, memory layout, devices, ABI artifacts)

------------------------------------------------------------

## Milestone 1 — MVP: validated scheduling v0 (done)

Scope
- Input: directed demands src_slot to dst_slot with bits_total
- Model: tick scheduling under STRICT1
- Output: schedule plus validator report and reproducible metrics

Key artifacts
- Scheduler I/O v0 contract: doc/scheduler_io_v0.md
- STRICT1 model spec: doc/strict1_model_v0.md
- Validator and metrics: copyspace-validate
- Two strategies for comparison: copyspace-solve (baseline and greedy)
- Demo runner: scripts/scheduler/demo_run.py
- Reference benchmark pack (seeded): scripts/scheduler/tests/ref_pack

------------------------------------------------------------

## Milestone 2 — CI gating and pilot helpers (done)

- Pilot intake and quickstart docs:
  - doc/partners/pilot_intake.md
  - doc/partners/quickstart_pilot.md
- CI gate recipe for partners:
  - doc/partners/ci_gate_recipe.md
  - doc/partners/ci_gate_workflow_example.yml
- One-command pilot runner:
  - copyspace-pilot

------------------------------------------------------------

## Milestone 3 — Release and repo hygiene (done)

Goal: make it easy to reference a stable version and accept pilot requests and contributions.

Deliverables
1) Release hygiene
- Confirm the current released version and tags match pyproject.toml.
- Publish a GitHub Release for the current version with short notes and quickstart commands.

2) Issue templates
- Pilot request: collect workload shape, constraints, and acceptance criteria
- Bug report: collect instance, schedule, and validator report

3) Contribution workflow
- CONTRIBUTING.md: keep aligned with current CI and scripts
- PR checklist: tests and doc sync expectations

------------------------------------------------------------

## Milestone 4 — Cross-platform UX (done)

Goal: a user can run core pilot and bench workflows on Linux, macOS, and Windows without requiring shell scripts.

Current state
- CI builds native tools via CMake on Linux, macOS, and Windows.
- Native tool release artifacts exist.

Remaining
1) Python-first orchestration
- Ensure user-facing flows have Python entrypoints (pilot, demo, bench smoke mode).
- Keep shell scripts as optional developer conveniences.

2) Documentation hygiene
- Make it explicit which interfaces are stable for external users:
  - copyspace-* entrypoints
  - doc contracts and schemas

3) CI coverage
- Add or extend CI checks that run the Python-first flows on at least one platform profile.

------------------------------------------------------------

## Milestone 5 — Bench and regression signals (done)

Goal: deterministic, automated signals for bench-level regressions with bounded runtime.

Delivered
- CI includes a deterministic bench-smoke job (skipped on pull_request).
- Regression signal policy: doc/bench_regression_policy.md
- Optional extended runs: .github/workflows/bench_extended.yml (workflow_dispatch + weekly schedule)

------------------------------------------------------------

## Milestone 6 — Scheduler scalability signals (done)

Goal: catch regressions related to large instances and long schedules without slowing PR CI.

Deliverables
- Add reproducible stress smoke for scheduler v0 (solve plus validate) with bounded runtime.
- Keep artifacts small (prefer reports and summaries over huge schedule JSON files).
- Add explicit CI coverage (job name and trigger policy).

------------------------------------------------------------

## Milestone 7 — Post-release audit and hardening (done)

Goal: make post-release quality and partner-facing surface area easier to review and maintain.

Deliverables
- Audit v0 doc: inventory of stable interfaces and surfaces
  - doc: doc/audit_v0.md
  - includes: CLI entrypoints, contracts/schemas, environment variables, file formats, compatibility notes
- Packaging sanity in CI (release-adjacent)
  - build: python -m build
  - check: twine check dist/*
- Trusted publishing decision
  - doc: update doc/pypi_publish.md with a short section: trusted publishing status (enabled or not) and rationale

------------------------------------------------------------

## Milestone 8 — Quality audit report and follow-ups (done)

Goal: produce a short, actionable report about code, docs, and CI alignment, with prioritized follow-ups.

Deliverables
- Audit report v0
  - doc: doc/audit_report_v0.md
  - includes: evidence (CI jobs and checks), drift checks (versions and references), and a prioritized follow-up list
- Follow-ups triage
  - Move accepted follow-ups into doc/status.md Next (prioritized) only

## Non-goals (current scope)

- No topology or routing selection
- No address-level allocation or validation inside endpoints (src_bit or dst_bit)
- No global optimality claims
