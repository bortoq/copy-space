#!/bin/sh
set -eu

REPEATS="${C3_STAGED_REPEATS:-3}"

i=1
while [ "$i" -le "$REPEATS" ]; do
  echo "[c3-staged] run $i/$REPEATS"
  C3_SKIP_STABILITY=1 sh scripts/tdd/run_c3_minimal.sh >"tmp/c3_staged_run_$i.log"
  i=$((i + 1))
done

echo "OK: C3 staged gate passed ${REPEATS}/${REPEATS}"
