#!/bin/sh
set -eu
runs="${RV32_SERVICE_FULL_RELEASE_REPEATS:-3}"
i=1
while [ "$i" -le "$runs" ]; do
  sh scripts/tdd/run_rv32_service_release_full.sh >/dev/null
  i=$((i+1))
done
echo "OK rv32 service full release gate ${runs}/${runs}"
