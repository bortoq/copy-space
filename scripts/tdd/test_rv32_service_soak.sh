#!/bin/sh
set -eu
runs="${RV32_SERVICE_SOAK_RUNS:-20}"
i=1
while [ "$i" -le "$runs" ]; do
  sh scripts/tdd/test_rv32_service_runtime_path.sh >/dev/null
  i=$((i+1))
done
echo "OK rv32 service soak ${runs}x"
