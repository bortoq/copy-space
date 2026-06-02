#!/bin/sh
set -eu

mkdir -p tmp/c3_r6
i=1
while [ "$i" -le 3 ]; do
  C3_SKIP_STABILITY=1 scripts/tdd/run_c3_minimal.sh >"tmp/c3_r6/run_$i.log"
  i=$((i+1))
done

echo "OK c3 r6 stability 3/3"
