# C3 MVP Test Set Freeze

Status: frozen in S10.
Date: 2026-06-01.

## Core set (20)

1. `test_c3_m0_stop_contract.sh`
2. `test_c3_trace_diff.sh`
3. `test_c3_layout.sh`
4. `test_c3_fetch_only.sh`
5. `test_c3_fetch_trace_diff.sh`
6. `test_c3_decode_known_unknown.sh`
7. `test_c3_decode_trace_diff.sh`
8. `test_c3_exec_mvp5.sh`
9. `test_c3_exec_mvp5_trace_diff.sh`
10. `test_c3_mode_parity.sh`
11. `test_c3_native_addi_trace_diff.sh`
12. `test_c3_native_add_trace_diff.sh`
13. `test_c3_native_sw_trace_diff.sh`
14. `test_c3_native_beq_trace_diff.sh`
15. `test_c3_native_jal_trace_diff.sh`
16. `test_c3_mem_run_diff.sh`
17. `test_c3_branch_run_diff.sh`
18. `test_c3_mem_subword_run_diff.sh`
19. `test_c3_trace_schema.sh`
20. `test_c3_repro_bundle.sh`

## Performance/budget set

- `test_c3_mvp5_budget.sh`
- `test_c3_mem_budget.sh`
- `test_c3_branch_budget.sh`
- `test_c3_mem_subword_budget.sh`
- `test_c3_budget.sh`

## Release gates

- `run_c3_staged.sh` (3/3)
- `run_rv32i_minimal.sh` (C2 no-regression)
