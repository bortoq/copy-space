#!/bin/sh
set -eu
sh scripts/tdd/test_rv32m_channel_timeout_recovery.sh >/dev/null
sh scripts/tdd/test_rv32m_loop_watchdog.sh >/dev/null
# recovery check: after watchdog we can still run smoke
sh scripts/tdd/test_rv32m_e2e_universal_loop.sh >/dev/null
echo "OK rv32 service recovery"
