#!/bin/sh
set -eu

# Single-goal minimal gate: VM trace + RV32I staged path

sh scripts/tdd/test_vmrun_trace_jsonl.sh
sh scripts/tdd/test_rv32i_mvp_trace.sh
sh scripts/tdd/test_rv32i_staged_plan.sh
sh scripts/tdd/test_rv32i_emitter_contract.sh

echo "OK: RV32I minimal gate passed"
