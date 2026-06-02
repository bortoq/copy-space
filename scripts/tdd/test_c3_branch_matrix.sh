#!/bin/sh
set -eu
scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_branch_matrix.f0 --dump-testg 29 --expect-hex 0100000024670000000000000000000006000000010101010100000024 >/dev/null
echo "OK c3 branch matrix"
