#!/bin/sh
set -eu
scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_mem_sw_lw_native.f0 --dump-testg 24 --expect-hex 01000000100000200300000000000000020000000000002a >/dev/null
echo "OK c3 mem sw/lw native"
