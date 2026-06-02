#!/bin/sh
set -eu
runs="${RV32_SERVICE_STAB_RUNS:-10}"
i=1
while [ "$i" -le "$runs" ]; do
  sh scripts/tdd/test_rv32m_e2e_universal_loop.sh >/dev/null
  i=$((i+1))
done
echo "OK rv32 service stability ${runs}x"
