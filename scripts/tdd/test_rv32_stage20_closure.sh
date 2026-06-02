#!/bin/sh
set -eu

sh scripts/tdd/test_rv32_c3_run_shortcuts_inventory.sh >/dev/null
sh scripts/tdd/test_rv32_c3_unsupported_trap_contract.sh >/dev/null
sh scripts/tdd/test_rv32_c3_run_generator_lint.sh >/dev/null
sh scripts/tdd/test_rv32_sha_profile_semantics.sh >/dev/null
sh scripts/tdd/test_rv32_guest_run_contract.sh >/dev/null
sh scripts/tdd/test_rv32_guest_lifecycle_negative.sh >/dev/null
sh scripts/tdd/test_rv32_sha256_three_binary_e2e.sh >/dev/null
sh scripts/tdd/test_rv32_stage20_evidence_bundle.sh >/dev/null

echo "OK rv32 stage20 closure"
