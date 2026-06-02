#!/bin/sh
set -eu
sh scripts/tdd/test_c3_trace_diff.sh >/dev/null
sh scripts/tdd/test_c3_m_run_diff.sh >/dev/null
sh scripts/tdd/test_c3_m_mul4_run_diff.sh >/dev/null
sh scripts/tdd/test_c3_m_div4_run_diff.sh >/dev/null
sh scripts/tdd/test_c3_m_div_corner_run_diff.sh >/dev/null
echo "OK rv32 service trace diff full"
