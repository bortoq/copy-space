#!/bin/sh
# run_rv32m_full_release.sh — unified runner for ALL RV32M release gates
set -eu

TMPDIR="$(mktemp -d tmp/rv32m_full_release.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

total=0
pass=0
fail=0
failed_gates=""

record() {
  local name="$1"
  local rc="$2"
  total=$((total + 1))
  if [ "$rc" -eq 0 ]; then
    pass=$((pass + 1))
    echo "  PASS: $name"
  else
    fail=$((fail + 1))
    failed_gates="$failed_gates $name"
    echo "  FAIL: $name"
  fi
}

echo "=== RV32M Full Release Gate ==="
echo ""

echo "--- 1. Items 1-6: C3 Minimal ---"
if sh scripts/tdd/run_c3_minimal.sh >"$TMPDIR/c3_minimal.log" 2>&1; then
  record "C3 minimal" 0
else
  record "C3 minimal" 1
fi

echo ""
echo "--- 2. RV32I Minimal ---"
if sh scripts/tdd/run_rv32i_minimal.sh >"$TMPDIR/rv32i_minimal.log" 2>&1; then
  record "RV32I minimal" 0
else
  record "RV32I minimal" 1
fi

echo ""
echo "--- 3. Item 7: Loader Rollout (full) ---"
if sh scripts/tdd/run_rv32m_loader_rollout.sh full >"$TMPDIR/loader_rollout.log" 2>&1; then
  record "Loader rollout full" 0
else
  record "Loader rollout full" 1
fi

echo ""
echo "--- 4. Item 8: Universal Loop ---"
for g in test_rv32m_loop_smoke test_rv32m_loop_watchdog test_rv32m_unified_entrypoint \
         test_rv32m_slice_independence test_rv32m_e2e_universal_loop test_rv32m_loop_stability; do
  if sh "scripts/tdd/${g}.sh" >"$TMPDIR/${g}.log" 2>&1; then
    record "$g" 0
  else
    record "$g" 1
  fi
done

echo ""
echo "--- 5. Item 9: Channel ABI ---"
for g in test_rv32m_channel_abi_contract test_rv32m_channel_io_roundtrip \
         test_rv32m_channel_timeout_recovery test_rv32m_channel_stop_abi \
         test_rv32m_channel_abi_compat; do
  if sh "scripts/tdd/${g}.sh" >"$TMPDIR/${g}.log" 2>&1; then
    record "$g" 0
  else
    record "$g" 1
  fi
done

echo ""
echo "--- 6. Item 10: E2E ---"
for g in test_rv32m_external_e2e_smoke test_rv32m_external_e2e_coverage \
         test_rv32m_e2e_release_gate; do
  if sh "scripts/tdd/${g}.sh" >"$TMPDIR/${g}.log" 2>&1; then
    record "$g" 0
  else
    record "$g" 1
  fi
done

echo ""
echo "=============================="
echo "Full Release Gate Summary: ${pass}/${total} passed, ${fail} failed"
if [ "$fail" -gt 0 ]; then
  echo "Failed gates:${failed_gates}"
  exit 1
fi
echo "ALL FULL RELEASE GATES PASSED"
