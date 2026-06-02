#!/bin/sh
set -eu

scripts/forth0/run_f0.sh \
  --in src/forth0/tests/test_c3_m0_stop_contract.f0 \
  --dump-testg 20 \
  --expect-hex 0300000020ffffffff000001000000000a000000 \
  >/dev/null

echo "OK c3 m0 stop contract"
