#!/bin/sh
set -eu
scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_mem_bounds_fault.f0 --dump-testg 20 --expect-hex 040000000c0000202300ffffff00000001000000 >/dev/null
echo "OK c3 mem bounds fault"
