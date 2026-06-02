#!/bin/sh
set -eu

scripts/forth0/run_f0.sh \
  --in src/forth0/tests/test_c3_dispatch_matrix.f0 \
  --dump-testg 15 \
  --expect-hex 0301010101010000000018ffffffff \
  >/dev/null

echo "OK c3 dispatch matrix"
