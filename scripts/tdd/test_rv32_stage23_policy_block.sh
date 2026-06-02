#!/bin/sh
set -eu

# Stage-23 policy block must be based on executable prerequisites,
# not roadmap status markers (to avoid circular deadlock).

sh scripts/tdd/test_rv32_c3_run_generator_lint.sh >/dev/null
sh scripts/tdd/test_rv32_guest_run_contract.sh >/dev/null
sh scripts/tdd/test_rv32_c3_unsupported_trap_contract.sh >/dev/null
sh scripts/tdd/test_rv32_sha_profile_semantics.sh >/dev/null

# Evidence path must remain healthy.
sh scripts/tdd/test_rv32_stage20_evidence_bundle.sh >/dev/null

echo "OK rv32 stage23 policy block"
