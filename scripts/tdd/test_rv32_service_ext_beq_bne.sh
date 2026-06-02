#!/bin/sh
set -eu

# Stage-20 replacement gate:
# exercise bounded execution + stop/trap ABI through in-space runtime.
sh scripts/tdd/test_rv32m_loop_watchdog.sh >/dev/null
sh scripts/tdd/test_rv32m_e2e_universal_loop.sh >/dev/null
sh scripts/tdd/test_rv32m_channel_stop_abi.sh >/dev/null

echo "OK rv32 service ext beq/bne (in-space replacement)"
