#!/bin/sh
set -eu

fail=0

tests="
scripts/tdd/test_forth0c.sh
scripts/tdd/test_vmerr_diag.sh
scripts/tdd/test_vmrun_strict_align32.sh
scripts/tdd/test_vmrun_trace_jsonl.sh
scripts/tdd/test_c3_m0_stop_contract.sh
scripts/tdd/test_c3_trace_diff.sh
scripts/tdd/test_rv32i_mvp_trace.sh
scripts/tdd/test_rv32i_staged_plan.sh
scripts/tdd/test_rv32i_emitter_contract.sh
"

for t in $tests; do
  echo
  echo "[tdd] RUN $t"
  rc=0
  if sh "$t"; then rc=0; else rc=$?; fi
  if [ "$rc" -eq 0 ]; then
    echo "[tdd] OK  $t"
  else
    echo "[tdd] FAIL $t"
    fail=1
  fi
done

exit "$fail"
