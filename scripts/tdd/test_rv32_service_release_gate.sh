#!/bin/sh
set -eu

runs="${RV32_SERVICE_RELEASE_REPEATS:-3}"
i=1
while [ "$i" -le "$runs" ]; do
  sh scripts/tdd/run_rv32_service_release.sh >/dev/null
  i=$((i+1))
done

echo "OK rv32 service release gate ${runs}/${runs}"
