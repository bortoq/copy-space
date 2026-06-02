#!/bin/sh
set -eu
scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_arith_fault.f0 --dump-testg 20 --expect-hex 0500000014020040330000000000000003000000 >/dev/null
echo "OK c3 arithmetic fault"
