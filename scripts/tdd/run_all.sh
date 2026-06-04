#!/bin/sh
set -eu

sh scripts/tdd/run_rv32_space_closure.sh
sh scripts/tdd/test_space_minimal_host_contract.sh
sh scripts/tdd/test_resident_job_descriptor_proof.sh
sh scripts/tdd/test_resident_job_selection_proof.sh
sh scripts/tdd/test_resident_tool_invocation_proof.sh
sh scripts/tdd/test_resident_toolchain_control_proof.sh
sh scripts/tdd/test_resident_copicode_artifact_proof.sh
sh scripts/tdd/test_resident_copicode_handoff_proof.sh

echo "OK anticrisis minimal baseline"
