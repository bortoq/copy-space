#!/bin/sh
set -eu

TARGET="scripts/tdd/test_rv32_freertos_channel_io_e2e.sh"
[ -f "$TARGET" ] || { echo "FAIL: missing $TARGET" >&2; exit 1; }

# Forbid known host-helper execution paths in active three-binary FreeRTOS gate.
F1="rv32i"; F2="_mvp_check.py"
F3="riscv_"; F4="trace_to_f0.py"
F5="riscv_"; F6="emulator.py"
F7="scripts/forth0/"; F8="run_f0.sh"
F9="test_sha256_"; F10="demo_in_space.sh"

FORBID="
${F1}${F2}
${F3}${F4}
${F5}${F6}
${F7}${F8}
${F9}${F10}
"

for p in $FORBID; do
  if rg -n --fixed-strings "$p" "$TARGET" >/dev/null 2>&1; then
    echo "FAIL: hidden helper path in $TARGET -> $p" >&2
    exit 1
  fi
done

# 3/3 deterministic interactive proof.
sh "$TARGET" >/dev/null
sh "$TARGET" >/dev/null
sh "$TARGET" >/dev/null

echo "OK rv32 freertos three-binary interactive e2e"
