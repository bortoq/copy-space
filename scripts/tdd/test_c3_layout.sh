#!/bin/sh
set -eu

scripts/forth0/run_f0.sh \
  --in src/forth0/tests/test_c3_layout.f0 \
  --dump-testg 20 \
  --expect-hex 0100100000102000104000120000200000108020 \
  >/dev/null

echo "OK c3 layout"
