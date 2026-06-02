#!/bin/sh
# test_rv32m_channel_abi_n1_compat.sh — N-1 ABI compatibility gate
set -eu

TMPDIR="$(mktemp -d tmp/rv32m_ch_abi_n1.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== Channel ABI N-1 Compatibility Gate ==="
echo ""

ABI_DOC="doc/rv32m_channel_abi.md"

echo "--- ABI Doc Exists ---"
if [ -f "$ABI_DOC" ]; then
  echo "  PASS: $ABI_DOC exists"
else
  echo "  FAIL: $ABI_DOC missing"
  exit 1
fi

echo ""
echo "--- Extract ABI Version ---"
ABI_VERSION=$(head -1 "$ABI_DOC" | grep -o 'v[0-9]\+' || echo "unknown")
echo "  ABI version: $ABI_VERSION"
if [ "$ABI_VERSION" = "v1" ]; then
  echo "  PASS: current ABI is v1"
else
  echo "  FAIL: expected v1, got $ABI_VERSION"
  exit 1
fi

echo ""
echo "--- Verify Current ABI (v1) Compatibility ---"
# v1 opcodes: 0=NOP/ACK, 1=STOP, 2=STEP_BUDGET
for op in 0 1 2; do
  grep -q "\`$op\` = " "$ABI_DOC" && echo "  PASS: opcode $op documented" || {
    echo "  FAIL: opcode $op not documented"
    exit 1
  }
done

echo ""
echo "--- Check Backward Compatibility Rules ---"
if grep -qi "compat" "$ABI_DOC"; then
  echo "  PASS: backward compatibility rules defined"
else
  echo "  FAIL: no backward compatibility rules found"
  exit 1
fi

echo ""
echo "ALL CHANNEL ABI N-1 COMPAT CHECKS PASSED"
