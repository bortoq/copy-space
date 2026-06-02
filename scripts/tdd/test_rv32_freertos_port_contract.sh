#!/usr/bin/env bash
set -euo pipefail

bash scripts/tdd/test_rv32_runtime_abi_ops.sh >/dev/null
bash scripts/tdd/test_rv32_three_binary_launcher_contract.sh >/dev/null
bash scripts/tdd/test_rv32_sha256_three_binary_e2e.sh >/dev/null
bash scripts/tdd/test_rv32_stage20_contract_gate.sh >/dev/null

[ -f doc/freertos_port.md ]
[ -f doc/freertos_port_status.md ]
rg -q "3-binary" doc/freertos_port.md
rg -q "Host-assisted execution: forbidden" doc/freertos_port_status.md

echo "OK rv32 freertos port contract"
