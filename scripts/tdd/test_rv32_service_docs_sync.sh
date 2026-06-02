#!/bin/sh
set -eu

for f in doc/rv32_service_abi.md doc/rv32_service_quickstart.md doc/rv32_service_runbook.md doc/rv32_service_skip_policy.md doc/rv32_service_skip_policy.json; do
  test -f "$f"
done

rg -n "tick|max_ticks|watchdog_ticks" doc/rv32_service_abi.md doc/rv32_service_quickstart.md >/dev/null
rg -n "N/N-1|compat" doc/rv32_service_abi.md >/dev/null

echo "OK rv32 service docs sync"
