# FreeRTOS Usable Contract (Stage 46.5.6)

## Definition of "usable"
FreeRTOS is considered usable only if an operator can:
1. Boot a compiled RV32 FreeRTOS guest in strict 3-binary mode.
2. Interact with the guest via runtime ABI channel I/O only.
3. Receive deterministic responses for the same scripted session.

Strict 3-binary mode means exactly:
1. Runtime VM binary.
2. In-space RISC-V emulator binary/image.
3. Guest FreeRTOS RV32 binary.

## Runtime assistance prohibition
During guest execution semantics, the system must not depend on:
- host-side Python RV execution,
- host-side shell/Forth0 execution paths,
- hidden translation/emulation helpers.

Test orchestration scripts are allowed only as harnesses; they must not replace guest execution semantics.

## Required green set
The contract is satisfied only when all gates below are green in current workspace state:
- `scripts/tdd/test_rv32_freertos_build_profile.sh` (46.5.1)
- `scripts/tdd/test_rv32_freertos_port_smoke.sh` (46.5.2)
- `scripts/tdd/test_rv32_freertos_channel_io_e2e.sh` (46.5.3)
- `scripts/tdd/test_rv32_freertos_three_binary_interactive_e2e.sh` (46.5.4)
- `scripts/tdd/test_rv32_freertos_release_enforcement.sh` (46.5.5)
- `scripts/tdd/test_rv32_stage20_contract_gate.sh` (base no-host-assistance contract)

## Closure gate
- `scripts/tdd/test_rv32_freertos_usable_contract.sh`
