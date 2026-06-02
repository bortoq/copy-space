# RV32 C3 Unsupported-Instruction Trap Contract (Stage-23)

Status: draft baseline (contract-first).

## Scope
This contract defines deterministic behavior when `C3_RUN` decodes an opcode/funct tuple
outside the currently supported semantic profile.

## Required behavior
- Unsupported decode tuple must not silently fall through to normal execution path.
- Unsupported decode tuple must produce deterministic stop/trap observable via runtime ABI.
- Runtime-observable outputs must be stable for same guest input and budget profile.

## Canonical stop mapping (baseline)
- Stop category: `unsupported_decode`.
- ABI-visible signal path:
  - `STATUS` (`op=6`) remains readable and non-crashing,
  - `READ_REGS/READ_MEM` remain readable for post-mortem.
- `stop_reason` encoding is frozen by implementation tests once unified-dispatch path is landed.

## Non-goals in current baseline
- Full numeric trap-code freeze is postponed until `C3_RUN` unified dispatch replaces MVP shortcuts.
