#!/bin/sh
set -eu
sh scripts/tdd/test_rv32m_loop_watchdog.sh >/dev/null
sh scripts/tdd/test_vmerr_diag.sh >/dev/null
echo "OK rv32 service safety limits"
