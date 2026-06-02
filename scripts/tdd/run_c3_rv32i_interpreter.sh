#!/bin/sh
set -eu

sh scripts/tdd/test_c3_add32_smoke.sh
sh scripts/tdd/test_c3_fetch_decode_smoke.sh
sh scripts/tdd/test_c3_exec_rvi_smoke.sh
sh scripts/tdd/test_c3_interpreter_loop.sh
sh scripts/tdd/test_c3_m0_stop_contract.sh
sh scripts/tdd/test_c3_trace_schema.sh
sh scripts/tdd/test_c3_trace_diff.sh
sh scripts/tdd/test_c3_budget.sh
sh scripts/tdd/test_c3_staged.sh
sh scripts/tdd/test_c3_channel_e2e.sh
sh scripts/tdd/test_c3_external_binary_e2e.sh

echo "OK: C3 RV32I interpreter release gate passed"
