#!/bin/sh
set -eu

for insn in addi lw sw beq bne; do
  rg -n --fixed-strings -- "- \`${insn}\`" doc/rv32_sha_profile_minimal.md >/dev/null
done

# Stage-23 semantic hardening prerequisites.
sh scripts/tdd/test_rv32_c3_run_shortcuts_inventory.sh >/dev/null

sh scripts/tdd/test_rv32_runtime_abi_ops.sh >/dev/null
sh scripts/tdd/test_rv32_sha_directed_vectors.sh >/dev/null
sh scripts/tdd/test_rv32_guest_lifecycle_contract.sh >/dev/null
sh scripts/tdd/test_rv32_guest_lifecycle_negative.sh >/dev/null
sh scripts/tdd/test_rv32_guest_run_contract.sh >/dev/null

# Determinism: repeated lifecycle+run contract should remain green.
i=1
while [ "$i" -le 3 ]; do
  sh scripts/tdd/test_rv32_guest_lifecycle_contract.sh >/dev/null
  sh scripts/tdd/test_rv32_guest_run_contract.sh >/dev/null
  i=$((i+1))
done

echo "OK rv32 sha profile semantics"
