#!/bin/sh
set -eu
scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_native_sw.f0 --dump-testg 28 --expect-hex 010000000c2300000000000000000000030000000000000000000008 >/dev/null
echo "OK c3 native sw"
