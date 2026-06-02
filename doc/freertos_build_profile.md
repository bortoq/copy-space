# FreeRTOS RV32 Build Profile (Stage 46.5.1)

## Contract scope
This profile freezes the guest build/boot envelope for FreeRTOS in strict 3-binary mode:
1. Runtime VM binary
2. In-space RV emulator binary
3. FreeRTOS RV32 guest binary

No host-side RV execution path is allowed in runtime correctness.

## 1) ISA/ABI freeze
- Architecture: `rv32im`
- ABI: `ilp32`
- Endianness: little-endian
- Calling convention: RISC-V ELF psABI for RV32 `ilp32`
- Floating-point ABI: none (`soft`)

Recommended compile flags baseline:
- `-march=rv32im -mabi=ilp32`
- `-ffreestanding -fno-builtin`
- `-fdata-sections -ffunction-sections`
- `-fno-omit-frame-pointer` (debug-friendly; optional for release)

## 2) Linker/memory map freeze
Guest image is loaded through runtime ABI `LOAD_CODE` as a flat RV32 payload.

Fixed logical regions:
- `.text/.rodata`: executable code and constants
- `.data`: initialized RW data
- `.bss`: zero-init RW data
- `heap`: dynamic allocation region used by FreeRTOS heap implementation
- `stack`: task/system stacks
- `tick/control`: scheduler tick/accounting data visible only via guest memory model

Entry point contract:
- Guest starts at `_start` address from linked image entry.
- Loader/runtime must not patch semantics beyond load addressing.

## 3) Boot contract freeze
Mandatory boot chain:
1. `_start`
2. crt init (`.data` init, `.bss` zero)
3. platform init required for timer/interrupt abstraction used by port
4. `vTaskStartScheduler()`

Restrictions:
- No host Python/shell/Forth0 helper in guest execution semantics.
- Runtime interaction only via VM+emulator channel ABI (LOAD_CODE/RUN/STEP/READ_REGS/READ_MEM/WRITE_MEM).

## 4) Stage 46.5.1 acceptance
Stage 46.5.1 is complete only when:
- This document exists and includes the frozen ISA/ABI, memory map, and boot chain.
- `scripts/tdd/test_rv32_freertos_build_profile.sh` is green.
