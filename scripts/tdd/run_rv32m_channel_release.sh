#!/bin/sh
# run_rv32m_channel_release.sh — channel ABI production release gate
set -eu

TMPDIR="$(mktemp -d tmp/rv32m_channel_release.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

fail=0
echo "=== Channel ABI Release Gate ==="
echo ""

echo "--- Channel ABI Contract ---"
if sh scripts/tdd/test_rv32m_channel_abi_contract.sh >"$TMPDIR/contract.log" 2>&1; then
  echo "  PASS: channel ABI contract"
else
  echo "  FAIL: channel ABI contract"
  fail=1
fi

echo ""
echo "--- Channel Stop ABI ---"
if sh scripts/tdd/test_rv32m_channel_stop_abi.sh >"$TMPDIR/stop_abi.log" 2>&1; then
  echo "  PASS: channel stop ABI"
else
  echo "  FAIL: channel stop ABI"
  fail=1
fi

echo ""
echo "--- Channel IO Roundtrip ---"
if sh scripts/tdd/test_rv32m_channel_io_roundtrip.sh >"$TMPDIR/io_roundtrip.log" 2>&1; then
  echo "  PASS: channel IO roundtrip"
else
  echo "  FAIL: channel IO roundtrip"
  fail=1
fi

echo ""
echo "--- Channel Timeout Recovery ---"
if sh scripts/tdd/test_rv32m_channel_timeout_recovery.sh >"$TMPDIR/timeout_recovery.log" 2>&1; then
  echo "  PASS: channel timeout recovery"
else
  echo "  FAIL: channel timeout recovery"
  fail=1
fi

echo ""
echo "--- Channel ABI Compat ---"
if sh scripts/tdd/test_rv32m_channel_abi_compat.sh >"$TMPDIR/compat.log" 2>&1; then
  echo "  PASS: channel ABI compat"
else
  echo "  FAIL: channel ABI compat"
  fail=1
fi

echo ""
echo "--- ABI Documentation Check ---"
if [ -f doc/rv32m_channel_abi.md ]; then
  echo "  PASS: doc/rv32m_channel_abi.md exists"
  ABI_VERSION=$(head -1 doc/rv32m_channel_abi.md | grep -o 'v[0-9]\+' || echo "unknown")
  if [ "$ABI_VERSION" = "v1" ]; then
    echo "  PASS: ABI version is $ABI_VERSION (expected v1)"
  else
    echo "  FAIL: ABI version is '$ABI_VERSION', expected v1"
    fail=1
  fi
else
  echo "  FAIL: doc/rv32m_channel_abi.md missing"
  fail=1
fi

echo ""
if [ "$fail" -eq 0 ]; then
  echo "ALL CHANNEL ABI RELEASE CHECKS PASSED"
else
  echo "SOME CHANNEL ABI RELEASE CHECKS FAILED"
fi
exit "$fail"
