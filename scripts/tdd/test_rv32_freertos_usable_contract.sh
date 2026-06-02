#!/bin/sh
set -eu

DOC="doc/freertos_usable_contract.md"
[ -f "$DOC" ] || { echo "FAIL: missing $DOC" >&2; exit 1; }

rg -q "Definition of \"usable\"" "$DOC"
rg -q "Runtime assistance prohibition" "$DOC"
rg -q "Required green set" "$DOC"

bash scripts/tdd/test_rv32_freertos_build_profile.sh >/dev/null
bash scripts/tdd/test_rv32_freertos_port_smoke.sh >/dev/null
bash scripts/tdd/test_rv32_freertos_channel_io_e2e.sh >/dev/null
bash scripts/tdd/test_rv32_freertos_three_binary_interactive_e2e.sh >/dev/null
bash scripts/tdd/test_rv32_freertos_release_enforcement.sh >/dev/null
bash scripts/tdd/test_rv32_stage20_contract_gate.sh >/dev/null

echo "OK rv32 freertos usable contract"
