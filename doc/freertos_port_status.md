# FreeRTOS Port Status

- Mode: 3-binary runtime only.
- Host-assisted execution: forbidden.
- Current phase: real FreeRTOS kernel port is NOT implemented; only synthetic RV32 guest harness exists.

## Required green gates
- `scripts/tdd/test_rv32_runtime_abi_ops.sh`
- `scripts/tdd/test_rv32_three_binary_launcher_contract.sh`
- `scripts/tdd/test_rv32_sha256_three_binary_e2e.sh`
- `scripts/tdd/test_rv32_stage20_contract_gate.sh`
- `scripts/tdd/test_rv32_freertos_port_contract.sh`
- `scripts/tdd/test_rv32_freertos_build_profile.sh`
- `scripts/tdd/test_rv32_freertos_port_smoke.sh`
- `scripts/tdd/test_rv32_freertos_channel_io_e2e.sh`
