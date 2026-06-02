#!/bin/sh
set -eu

scripts/forth0/run_f0.sh \
  --in src/forth0/tests/test_c3_native_addi.f0 \
  --dump-testg 24 \
  --expect-hex 010000000413000000000000000000000100000000000005 \
  >/dev/null

echo "OK c3 native addi"
