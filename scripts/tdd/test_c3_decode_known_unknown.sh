#!/bin/sh
set -eu

scripts/forth0/run_f0.sh \
  --in src/forth0/tests/test_c3_decode_known_unknown.f0 \
  --dump-testg 20 \
  --expect-hex 0300000004ffffffff0000000000000002000000 \
  >/dev/null

echo "OK c3 decode known/unknown"
