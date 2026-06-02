#!/bin/sh
# run_rv32m_e2e_release.sh — release gate for full E2E conformance (10.3.1)
set -eu

TMPDIR="$(mktemp -d tmp/rv32m_e2e_release.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

fail=0
echo "=== 10.3.1 E2E Release Gate ==="
echo ""

echo "--- Item 8: Universal Loop Gates ---"
for g in test_rv32m_loop_smoke test_rv32m_loop_watchdog test_rv32m_unified_entrypoint \
         test_rv32m_slice_independence test_rv32m_e2e_universal_loop test_rv32m_loop_stability; do
  if sh "scripts/tdd/${g}.sh" >"$TMPDIR/${g}.log" 2>&1; then
    echo "  PASS: ${g}"
  else
    echo "  FAIL: ${g}"
    fail=1
  fi
done

echo ""
echo "--- Item 7: Loader Gates (release phase) ---"
if sh scripts/tdd/run_rv32m_loader_rollout.sh release >"$TMPDIR/loader_rollout.log" 2>&1; then
  echo "  PASS: loader rollout (release)"
else
  echo "  FAIL: loader rollout (release)"
  fail=1
fi

echo ""
echo "--- Item 9: Channel ABI Gates ---"
for g in test_rv32m_channel_abi_contract test_rv32m_channel_io_roundtrip \
         test_rv32m_channel_timeout_recovery test_rv32m_channel_stop_abi \
         test_rv32m_channel_abi_compat; do
  if sh "scripts/tdd/${g}.sh" >"$TMPDIR/${g}.log" 2>&1; then
    echo "  PASS: ${g}"
  else
    echo "  FAIL: ${g}"
    fail=1
  fi
done

echo ""
echo "--- Item 10: E2E Gates ---"
for g in test_rv32m_external_e2e_smoke test_rv32m_external_e2e_coverage; do
  if sh "scripts/tdd/${g}.sh" >"$TMPDIR/${g}.log" 2>&1; then
    echo "  PASS: ${g}"
  else
    echo "  FAIL: ${g}"
    fail=1
  fi
done

echo ""
echo "--- Release Checklist Verification ---"
if [ -f doc/rv32m_release_checklist.md ]; then
  echo "  PASS: doc/rv32m_release_checklist.md exists"
else
  echo "  FAIL: doc/rv32m_release_checklist.md missing"
  fail=1
fi

echo ""
if [ "$fail" -eq 0 ]; then
  echo "ALL E2E RELEASE GATE CHECKS PASSED"
else
  echo "SOME E2E RELEASE GATE CHECKS FAILED"
fi
exit "$fail"
