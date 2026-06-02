#!/bin/sh
set -eu
sh scripts/tdd/test_rv32m_loop_smoke.sh >/dev/null
sh scripts/tdd/test_rv32m_loop_watchdog.sh >/dev/null
sh scripts/tdd/test_rv32m_unified_entrypoint.sh >/dev/null
# deterministic replay smoke (10x identical outcome)
i=1
while [ "$i" -le 10 ]; do
  sh scripts/tdd/test_rv32m_e2e_universal_loop.sh >/dev/null
  i=$((i+1))
done
echo "OK rv32 service runtime path"
