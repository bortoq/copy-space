# RV32I Closure Matrix (C3)

Status: active.
Date: 2026-06-01.
Scope: пункт `14.20.2` (RV32I closure audit before RV32M implementation).

## Risk assessment

1. Decode coverage gaps (medium): unknown opcode paths may silently diverge.
2. Branch corner-cases (medium-high): signed/unsigned branch semantics may regress.
3. Load/store corner-cases (high): bounds/alignment/sign-extension are regression-prone.
4. Stop/error contract drift (medium): illegal/memory faults may lose ABI compatibility.

## Edge-case to gate mapping

- Decode known/unknown:
  - `scripts/tdd/test_c3_decode_known_unknown.sh`
  - `scripts/tdd/test_c3_dispatch_matrix.sh`
- Branch semantics matrix:
  - `scripts/tdd/test_c3_branch_matrix.sh`
  - `scripts/tdd/test_c3_branch_matrix_trace_diff.sh`
- Memory alignment/bounds:
  - `scripts/tdd/test_c3_mem_align_fault.sh`
  - `scripts/tdd/test_c3_mem_bounds_fault.sh`
- Subword sign/zero extension:
  - `scripts/tdd/test_c3_mem_subword.sh`
  - `scripts/tdd/test_c3_mem_subword_trace_diff.sh`
- Stop/error and native no-regression:
  - `scripts/tdd/test_c3_m0_stop_contract.sh`
  - `scripts/tdd/test_c3_r6_no_regression.sh`

## Closure criterion for 14.20.2

- All mapped gates pass in one audit run.
- Audit artifact is generated (`tmp/c3_rv32i_closure_audit.json`).
- No open RV32I closure blockers in matrix scope.
