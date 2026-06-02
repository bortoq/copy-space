#!/bin/sh
# run_rv32m_loader_rollout.sh — phased rollout gate for RV32M loader (7.4)
# Runs all loader gates and verifies no-regression against existing gates.
set -eu

echo "=== 7.4 Loader Rollout Gate ==="
echo ""

# Feature flag
RV32M_IMAGE_LOADER_V1="${RV32M_IMAGE_LOADER_V1:-1}"
echo "RV32M_IMAGE_LOADER_V1=$RV32M_IMAGE_LOADER_V1"

if [ "$RV32M_IMAGE_LOADER_V1" != "1" ]; then
  echo "SKIP: loader v1 disabled by feature flag"
  exit 0
fi

# Phase check via argument
PHASE="${1:-full}"
echo "Phase: $PHASE"

case "$PHASE" in
  preflight)
    echo "Running preflight checks..."
    bash scripts/tdd/test_rv32m_image_format_contract.sh
    bash scripts/tdd/test_rv32m_loader_happy_path.sh
    ;;
  minimal)
    echo "Running minimal checks..."
    bash scripts/tdd/test_rv32m_image_format_contract.sh
    bash scripts/tdd/test_rv32m_loader_happy_path.sh
    bash scripts/tdd/test_rv32m_loader_rollback.sh
    bash scripts/tdd/test_rv32m_loader_timeout.sh
    bash scripts/tdd/test_rv32m_loader_integrity.sh
    echo "No-regression: run_c3_minimal.sh"
    bash scripts/tdd/run_c3_minimal.sh
    echo "No-regression: run_rv32i_minimal.sh"
    bash scripts/tdd/run_rv32i_minimal.sh
    ;;
  full|staged|release)
    echo "Running full checks..."
    bash scripts/tdd/test_rv32m_image_format_contract.sh
    bash scripts/tdd/test_rv32m_loader_happy_path.sh
    bash scripts/tdd/test_rv32m_loader_rollback.sh
    bash scripts/tdd/test_rv32m_loader_timeout.sh
    bash scripts/tdd/test_rv32m_loader_integrity.sh
    bash scripts/tdd/test_rv32m_loader_reproducibility.sh
    rm -rf tmp/rv32m_loader_*.?????? tmp/rv32m_format_test.*
    echo "3/3 repeat-stability check:"
    for i in 1 2 3; do
      echo "  run $i..."
      bash scripts/tdd/test_rv32m_loader_happy_path.sh >/dev/null 2>&1 || { echo "FAIL repeat $i"; exit 1; }
    done
    echo "OK 3/3"
    echo "No-regression: run_c3_minimal.sh"
    bash scripts/tdd/run_c3_minimal.sh
    echo "No-regression: run_rv32i_minimal.sh"
    bash scripts/tdd/run_rv32i_minimal.sh
    ;;
  *)
    echo "Unknown phase: $PHASE (use: preflight|minimal|full|staged|release)"
    exit 1
    ;;
esac

echo ""
echo "ALL 7.4 ROLLOUT CHECKS PASSED (phase=$PHASE)"
