# C3 Release Checklist (S10)

Status: active from S10.

## Mandatory

1. `sh scripts/tdd/run_c3_staged.sh` passes 3/3.
2. `sh scripts/tdd/run_rv32i_minimal.sh` passes (no C2 regression).
3. `sh scripts/tdd/test_c3_budget.sh` passes.
4. `doc/c3_mvp_test_set.md` and `doc/c3_known_limits.md` are up to date.
5. Repro bundle path works on synthetic mismatch (`test_c3_repro_bundle.sh`).

## Optional deep checks

1. `sh scripts/tdd/run_c3_minimal.sh` with stability enabled.
2. Inspect `tmp/c3_budget_s9/baseline.json` for drift trends.
3. Verify trace schema full+compact outputs after trace-related changes.
