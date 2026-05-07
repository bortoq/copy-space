#!/bin/sh
set -eu

fail=0

tests="
scripts/tdd/test_vmrep_tools.sh
scripts/tdd/test_vmerr_diag.sh
scripts/tdd/test_scratch_abi.sh
scripts/tdd/test_scratch_artifacts.sh
scripts/tdd/test_term0_desc_abi.sh
scripts/tdd/test_fail_bundle.sh
scripts/tdd/test_ptrprims.sh
scripts/tdd/test_art_doc_sync.sh
"

for t in $tests; do
  echo
  echo "[tdd] RUN $t"

  rc=0
  if [ "$t" = "scripts/tdd/test_ptrprims.sh" ]; then
    if bash "$t"; then rc=0; else rc=$?; fi
  else
    if sh "$t"; then rc=0; else rc=$?; fi
  fi

  if [ "$rc" -eq 0 ]; then
    echo "[tdd] OK  $t"
  else
    echo "[tdd] FAIL $t"
    fail=1
  fi
done

exit "$fail"
