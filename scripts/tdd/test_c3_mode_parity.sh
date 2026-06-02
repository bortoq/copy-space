#!/bin/sh
set -eu

mkdir -p tmp/c3_mode

C3_MODE=scaffold scripts/forth0/run_f0.sh \
  --in src/forth0/tests/test_c3_exec_mvp5.f0 \
  --dump-testg 37 \
  --keep \
  --tmpdir tmp/c3_mode/scaffold \
  >/dev/null

C3_MODE=native scripts/forth0/run_f0.sh \
  --in src/forth0/tests/test_c3_exec_mvp5_native_stub.f0 \
  --dump-testg 37 \
  --keep \
  --tmpdir tmp/c3_mode/native \
  >/dev/null

cmp -s tmp/c3_mode/scaffold/testg.bin tmp/c3_mode/native/testg.bin

echo "OK c3 mode parity"
