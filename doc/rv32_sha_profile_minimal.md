# RV32 SHA Minimal Profile (Stage-20)

Status: baseline for stage-20 semantic gates

Required instruction families for current canonical compiled guest path:
- `addi`
- `lw`
- `sw`
- `beq`
- `bne`

Execution invariants:
- deterministic lifecycle over repeated runs
- bounded-step watchdog progression
- protocol and bounds errors are fail-fast
