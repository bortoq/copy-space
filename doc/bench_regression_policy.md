# Bench regression policy (v0)

File: doc/bench_regression_policy.md

Goal: define what constitutes a performance regression for Copy-Space benches, and where the signal is reported or enforced.

This policy is intentionally conservative:
- correctness regressions hard-fail CI (validator errors, test failures)
- performance regressions are reported as a CI signal first (summary + artifacts), with optional hard limits only after we gain history and confidence

------------------------------------------------------------

## Scope

Bench families:
- Core benches (Python-first): copyspace-bench-core
  - pack, permute, bulkcopy
- Scheduler bench (Python-first): copyspace-bench-scheduler
  - validated scheduling, unified CSV v0 output

Primary environments:
- CI bench-smoke job (bounded runtime, deterministic inputs)
- Bench history workflow (time series for manual review)

------------------------------------------------------------

## Correctness vs performance regressions

Correctness regressions (hard-fail):
- make test / make tdd failures
- scheduler validation failures (copyspace-validate FAIL)
- bench tooling errors (non-zero exit, missing outputs)

Performance regressions (signal first, optionally hard-fail later):
- significant drops in throughput-like metrics on the canonical CI smoke profiles
- significant degradation of scheduler quality metrics (gap to lower bound) on canonical instances

------------------------------------------------------------

## Core bench metrics (pack, permute, bulkcopy)

Primary metric:
- vmrep_avg_bits_uniq_dst_per_tick
  Effective unique destination bits written per tick.
  Overlapping writes do not inflate it.

Secondary context:
- expected_bits_per_tick (upper bound style baseline for utilization-style interpretation)

Regression signal (v0):
- We report the metrics in CI step summary and store CSV artifacts.
- We do not hard-fail on metric deltas yet, because cross-run noise exists.

Future hard limits (deferred):
- After we accumulate history, we may add optional hard limits such as:
  - utilization floor: uniq / expected must stay above a chosen threshold
  - absolute floor for vmrep_avg_bits_uniq_dst_per_tick for each bench profile
  - or a comparison against a pinned baseline CSV committed in the repo

------------------------------------------------------------

## Scheduler bench metrics (validated scheduling)

Correctness requirements:
- schedules produced by solvers must PASS copyspace-validate under STRICT1 (bandwidth + coverage + model constraints)

Primary performance / quality signals:
- ticks_total (schedule length)
- lower_bound_ticks (reported by validator)
- gap_ticks and gap_to_lower_bound (ticks_total minus lower_bound_ticks)
- utilization-style metrics based on vmrep_avg_bits_uniq_dst_per_tick vs expected_bits_per_tick

Regression signal (v0):
- Report top rows in CI summary and store unified CSV artifacts.
- Manual review is based on trend (bench history) and on comparisons between solvers (baseline vs greedy).

------------------------------------------------------------

## Where the signal lives today

1) CI bench-smoke job
- Produces tmp/bench_smoke.csv and tmp/sched_smoke.csv (plus small markdown summaries)
- Appends summaries to the GitHub Actions job summary

2) Bench history (Pages) workflow
- Publishes the same smoke CSV and summaries as a time series

------------------------------------------------------------

## How to act on a suspected regression

When a regression is suspected:
- link the CI run ID or Pages run ID
- attach the CSV artifact(s)
- include git revision (git describe --tags --always)
- mention platform profile (ubuntu-latest, macos-latest, windows-latest)

