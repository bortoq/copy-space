#!/bin/sh
set -eu

sh scripts/tdd/test_rv32_service_abi_contract.sh
sh scripts/tdd/test_rv32_service_runtime_path.sh
sh scripts/tdd/test_rv32_service_isa_matrix.sh
sh scripts/tdd/test_rv32_service_loader_e2e.sh
sh scripts/tdd/test_rv32_service_loader_negative.sh
sh scripts/tdd/test_rv32_service_external_smoke.sh
sh scripts/tdd/test_rv32_service_external_coverage.sh
sh scripts/tdd/test_rv32_service_external_channel_blackbox.sh
sh scripts/tdd/test_rv32_service_no_host_deps.sh
sh scripts/tdd/test_rv32_service_recovery.sh
sh scripts/tdd/test_rv32_service_compat_n1.sh
sh scripts/tdd/test_rv32_service_slo.sh
sh scripts/tdd/test_rv32_service_fuzz_smoke.sh
sh scripts/tdd/test_rv32_service_safety_limits.sh
sh scripts/tdd/test_rv32_service_docs_sync.sh

echo "OK rv32 service release run"
