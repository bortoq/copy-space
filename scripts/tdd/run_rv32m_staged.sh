#!/bin/sh
set -eu

REPEATS="${RV32M_STAGED_REPEATS:-3}"

i=1
while [ "$i" -le "$REPEATS" ]; do
  echo "[rv32m-staged] run $i/$REPEATS — C3 minimal"
  C3_SKIP_STABILITY=1 sh scripts/tdd/run_c3_minimal.sh >"tmp/rv32m_staged_run_${i}_c3.log"

  echo "[rv32m-staged] run $i/$REPEATS — item 7 (loader)"
  sh scripts/tdd/run_rv32m_loader_rollout.sh minimal >"tmp/rv32m_staged_run_${i}_item7.log"

  echo "[rv32m-staged] run $i/$REPEATS — item 8 (loop)"
  for g in test_rv32m_loop_smoke test_rv32m_loop_watchdog test_rv32m_unified_entrypoint \
           test_rv32m_slice_independence test_rv32m_e2e_universal_loop test_rv32m_loop_stability; do
    sh "scripts/tdd/${g}.sh" >"tmp/rv32m_staged_run_${i}_${g}.log"
  done

  echo "[rv32m-staged] run $i/$REPEATS — item 9 (channel ABI)"
  for g in test_rv32m_channel_abi_contract test_rv32m_channel_io_roundtrip \
           test_rv32m_channel_timeout_recovery test_rv32m_channel_stop_abi \
           test_rv32m_channel_abi_compat; do
    sh "scripts/tdd/${g}.sh" >"tmp/rv32m_staged_run_${i}_${g}.log"
  done

  echo "[rv32m-staged] run $i/$REPEATS — item 10 (e2e)"
  for g in test_rv32m_external_e2e_smoke test_rv32m_external_e2e_coverage; do
    sh "scripts/tdd/${g}.sh" >"tmp/rv32m_staged_run_${i}_${g}.log"
  done

  i=$((i + 1))
done

echo "OK: RV32M staged gate passed ${REPEATS}/${REPEATS}"
