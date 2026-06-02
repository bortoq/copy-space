# FreeRTOS Port (RV32, 3-binary mode)

## Goal
Run a FreeRTOS RV32 guest in the existing 3-binary runtime path:
1. Runtime VM binary
2. In-space RV emulator binary/image
3. Guest RV32 binary

## 46.1 execution slice (status corrected: not a real FreeRTOS port)
This slice only established prerequisite checks and synthetic guest gates; it did NOT implement a real FreeRTOS kernel port.

### Preconditions (must stay green)
- Runtime ABI ops are executable (`LOAD_CODE/RUN/STEP/READ_REGS/READ_MEM/WRITE_MEM`).
- 3-binary launcher contract is executable.
- SHA-256 3-binary path stays green as baseline non-trivial guest proof.
- Stage-20 contract gate remains green (no host RV emulation in active correctness path).

### Artifacts
- This document (`doc/freertos_port.md`).
- Port status tracker (`doc/freertos_port_status.md`).
- Gate script: `scripts/tdd/test_rv32_freertos_port_contract.sh`.

### Definition of done for stage 46.1 (previous, now invalid for real FreeRTOS)
- FreeRTOS port contract gate is green.
- No host-assisted path is introduced.
- 3-binary runtime invariants remain green.
