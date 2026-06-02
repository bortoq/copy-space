#!/bin/sh
set -eu

DOC="doc/rv32_bootstrap_closure.md"
[ -f "$DOC" ] || { echo "FAIL: missing $DOC"; exit 1; }

for s in \
  'LOAD_CODE -> RUN/STEP -> READ_REGS/READ_MEM -> TRACE_INFO/TRACE_READ' \
  'STATUS' \
  'LOAD_CODE' \
  'RUN' \
  'STEP' \
  'READ_REGS' \
  'READ_MEM' \
  'WRITE_MEM' \
  'TRACE_INFO' \
  'TRACE_READ' \
  'временным переходным контрактом' \
  'proof-only' \
  'достаточным для начала реконструкции `space.*`' \
  'запрещено расширять host-side guest logic сверх bootstrap closure'
do
  rg -n --fixed-strings "$s" "$DOC" >/dev/null
done

for s in \
  'scripts/tdd/test_rv32_runtime_abi_ops.sh' \
  'scripts/tdd/test_rv32_guest_run_contract.sh' \
  'scripts/tdd/test_rv32_stage3_rv32i_runtime.sh' \
  'scripts/tdd/test_rv32_stage4_trace_runtime.sh' \
  'scripts/tdd/test_rv32_stage4_bootstrap_proof.sh' \
  'scripts/tdd/run_rv32_bootstrap_closure.sh'
do
  rg -n --fixed-strings "$s" "$DOC" >/dev/null
done

echo "OK rv32 bootstrap docs sync"
