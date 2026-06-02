#!/bin/sh
set -eu

sh scripts/tdd/test_rv32_runtime_abi_ops.sh
sh scripts/tdd/test_rv32_guest_run_contract.sh
sh scripts/tdd/test_rv32_stage3_rv32i_runtime.sh
sh scripts/tdd/test_rv32_stage4_trace_runtime.sh
sh scripts/tdd/test_rv32_stage4_bootstrap_proof.sh
sh scripts/tdd/test_rv32_bootstrap_docs_sync.sh
sh scripts/tdd/test_rv32_bootstrap_closure_contract.sh

echo "OK rv32 bootstrap closure"
