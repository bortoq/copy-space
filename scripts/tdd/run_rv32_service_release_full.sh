#!/bin/sh
set -eu

sh scripts/tdd/test_rv32_service_abi_contract.sh
sh scripts/tdd/test_rv32_service_runtime_path.sh
sh scripts/tdd/test_rv32_service_isa_matrix_full.sh
sh scripts/tdd/test_rv32_service_trace_diff_full.sh
sh scripts/tdd/test_rv32_service_trap_conformance.sh
sh scripts/tdd/test_rv32_service_mem_negative_full.sh
sh scripts/tdd/test_rv32_service_loader_arbitrary_e2e.sh
sh scripts/tdd/test_rv32_service_loader_profile_compat.sh
sh scripts/tdd/test_rv32_service_ext_add_addi.sh
sh scripts/tdd/test_rv32_service_ext_beq_bne.sh
sh scripts/tdd/test_rv32_service_ext_lw_sw.sh
sh scripts/tdd/test_rv32_service_space_contract_unchanged.sh
sh scripts/tdd/test_rv32_service_stability_10x.sh
sh scripts/tdd/test_rv32_service_soak.sh
sh scripts/tdd/test_rv32_service_no_host_deps.sh
sh scripts/tdd/test_rv32_guest_load_contract.sh
sh scripts/tdd/test_rv32_guest_run_contract.sh
sh scripts/tdd/test_stage23_minimal_freeze_scope.sh
sh scripts/tdd/test_stage23_daily_closure_report.sh
sh scripts/tdd/test_stage23_fast_path_order.sh
sh scripts/tdd/test_rv32_c3_run_shortcuts_inventory.sh
sh scripts/tdd/test_rv32_c3_dispatch_contract.sh
sh scripts/tdd/test_rv32_c3_unsupported_trap_contract.sh
sh scripts/tdd/test_rv32_c3_run_generator_lint.sh
sh scripts/tdd/test_rv32_stage20_contract_gate.sh
sh scripts/tdd/test_rv32_sha_profile_semantics.sh
sh scripts/tdd/test_rv32_sha256_three_binary_e2e.sh
sh scripts/tdd/test_rv32_freertos_three_binary_interactive_e2e.sh
sh scripts/tdd/test_rv32_three_binary_launcher_contract.sh
sh scripts/tdd/test_rv32_stage20_evidence_bundle.sh
sh scripts/tdd/test_rv32_freertos_release_enforcement.sh
sh scripts/tdd/test_rv32_stage20_closure.sh
sh scripts/tdd/test_rv32_stage23_policy_block.sh
sh scripts/tdd/test_rv32_stage23_completion_rule.sh
sh scripts/tdd/test_rv32_service_docs_sync.sh

echo "OK rv32 service full release run"
