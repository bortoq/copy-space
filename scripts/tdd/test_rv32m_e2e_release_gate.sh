#!/bin/sh
# test_rv32m_e2e_release_gate.sh — full E2E release readiness gate (10.3)
set -eu
echo "=== 10.3 E2E Release Gate ==="
echo "Running release readiness checks..."
echo ""

PHASES="preflight minimal staged"
for phase in $PHASES; do
  echo "Phase: $phase"
  case "$phase" in
    preflight)
      bash scripts/tdd/test_rv32m_image_format_contract.sh 2>&1 | tail -1
      bash scripts/tdd/test_rv32m_loader_happy_path.sh 2>&1 | tail -1
      ;;
    minimal)
      for g in test_rv32m_loader_rollback test_rv32m_loader_timeout test_rv32m_loader_integrity \
               test_rv32m_loop_smoke test_rv32m_loop_watchdog test_rv32m_channel_abi_contract \
               test_rv32m_channel_stop_abi test_rv32m_external_e2e_smoke; do
        bash "scripts/tdd/${g}.sh" >/dev/null 2>&1 && echo "  ${g}: PASS" || { echo "  ${g}: FAIL"; exit 1; }
      done
      ;;
    staged)
      for g in test_rv32m_unified_entrypoint test_rv32m_slice_independence \
               test_rv32m_e2e_universal_loop test_rv32m_loop_stability \
               test_rv32m_loader_reproducibility test_rv32m_channel_io_roundtrip \
               test_rv32m_channel_timeout_recovery test_rv32m_channel_abi_compat \
               test_rv32m_external_e2e_coverage; do
        bash "scripts/tdd/${g}.sh" >/dev/null 2>&1 && echo "  ${g}: PASS" || { echo "  ${g}: FAIL"; exit 1; }
      done
      ;;
  esac
done

echo ""
echo "ALL E2E RELEASE GATE CHECKS PASSED"
