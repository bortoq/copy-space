#!/bin/sh
set -eu
scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_mem_subword.f0 --dump-testg 36 --expect-hex 0100000020000050030000000000000006000000ffffff8000000080ffffff340000ff34 >/dev/null
echo "OK c3 mem subword"
