#!/bin/sh
set -eu

# Stage 20 contract gate: active release path must not rely on
# host-side RV trace/translation/emulation helpers at runtime.

ROOT="scripts/tdd/run_rv32_service_release_full.sh"
[ -f "$ROOT" ] || { echo "FAIL: missing $ROOT"; exit 1; }

TMPDIR="$(mktemp -d tmp/rv32_stage20_gate.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

# Collect direct script dependencies from release runner.
awk '/^sh scripts\/tdd\// { print $2 }' "$ROOT" > "$TMPDIR/scripts.list"

# Forbidden runtime-path helpers for stage 20 contract.
FORBID_PATTERNS="
rv32i_mvp_check.py
riscv_trace_to_f0.py
riscv_emulator.py
scripts/forth0/run_f0.sh
test_sha256_demo_in_space.sh
scripts/riscv/run_external_rv32i_corpus.py
"

failed=0
while IFS= read -r s; do
  [ "$s" = "scripts/tdd/test_rv32_stage20_contract_gate.sh" ] && continue
  [ -f "$s" ] || { echo "FAIL: listed script missing: $s"; failed=1; continue; }
  for p in $FORBID_PATTERNS; do
    if rg -n --fixed-strings "$p" "$s" >/dev/null 2>&1; then
      echo "FAIL: stage20 contract violation in $s -> references '$p'"
      failed=1
    fi
  done
done < "$TMPDIR/scripts.list"

if [ "$failed" -ne 0 ]; then
  exit 1
fi

echo "OK rv32 stage20 contract gate"
