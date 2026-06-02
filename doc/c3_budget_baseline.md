# C3 Budget Baseline (S9)

Status: active after S9 freeze.

Budget gate: `scripts/tdd/test_c3_budget.sh`

Tracked slices:
- `mvp5`
- `mem`
- `branch`
- `subword`

Per-slice metrics:
- `tok_bytes`
- `compile_ticks`
- `run_ticks`
- `ticks_per_1k_steps`

Policy:
- hard caps enforced by env defaults (`C3_*_MAX_*`)
- repeat stability: 3 runs (`C3_S9_REPEATS=3`)
- allowed degradation per metric vs run1 baseline: `<= 110%` (`C3_S9_MAX_DEGR_PCT`)

Artifacts:
- `tmp/c3_budget_s9/baseline.json`
- `tmp/c3_budget_s9/run_*/summary.txt`
