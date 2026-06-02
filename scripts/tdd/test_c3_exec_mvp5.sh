#!/bin/sh
set -eu

mode="${C3_MODE:-scaffold}"
enforce_native="${C3_ENFORCE_NATIVE_MVP5:-0}"
case "$mode" in
  scaffold) in_f0="src/forth0/tests/test_c3_exec_mvp5.f0" ;;
  native)   in_f0="src/forth0/tests/test_c3_exec_mvp5_native_stub.f0" ;;
  *) echo "ERROR: unsupported C3_MODE='$mode' (expected scaffold|native)" >&2; exit 2 ;;
esac

if [ "$enforce_native" = "1" ] && [ "$mode" != "native" ]; then
  echo "ERROR: C3_ENFORCE_NATIVE_MVP5=1 requires C3_MODE=native" >&2
  exit 1
fi

scripts/forth0/run_f0.sh \
  --in "$in_f0" \
  --dump-testg 37 \
  --expect-hex 01000000140000006f00000000000000050000000000000500000008000000080100000014 \
  >/dev/null

echo "OK c3 exec mvp5 mode=$mode"
