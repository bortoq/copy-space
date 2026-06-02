#!/bin/sh
set -eu

scripts/forth0/run_f0.sh \
  --in src/forth0/tests/test_c3_fetch_only.f0 \
  --dump-testg 20 \
  --expect-hex 020000000cdeadbeef0000000000000003000000 \
  >/dev/null

echo "OK c3 fetch-only"
