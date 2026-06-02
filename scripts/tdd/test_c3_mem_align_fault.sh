#!/bin/sh
set -eu
scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_mem_align_fault.f0 --dump-testg 20 --expect-hex 0400000008000020030000000200000001000000 >/dev/null
echo "OK c3 mem align fault"
