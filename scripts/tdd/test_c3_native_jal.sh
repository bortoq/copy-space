#!/bin/sh
set -eu
scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_native_jal.f0 --dump-testg 24 --expect-hex 01000000186f000000000000000000000500000000000014 >/dev/null
echo "OK c3 native jal"
