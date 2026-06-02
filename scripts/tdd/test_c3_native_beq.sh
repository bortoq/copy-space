#!/bin/sh
set -eu
scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_native_beq.f0 --dump-testg 21 --expect-hex 010000001463000000000000000000000400000001 >/dev/null
echo "OK c3 native beq"
