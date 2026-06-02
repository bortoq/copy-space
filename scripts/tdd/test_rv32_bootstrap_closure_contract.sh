#!/bin/sh
set -eu

ROOT="scripts/tdd/run_rv32_bootstrap_closure.sh"
[ -f "$ROOT" ] || { echo "FAIL: missing $ROOT"; exit 1; }

TMPDIR="$(mktemp -d tmp/rv32_bootstrap_contract.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

awk '/^sh scripts\/tdd\// { print $2 }' "$ROOT" > "$TMPDIR/scripts.list"

EXPECTED="
scripts/tdd/test_rv32_runtime_abi_ops.sh
scripts/tdd/test_rv32_guest_run_contract.sh
scripts/tdd/test_rv32_stage3_rv32i_runtime.sh
scripts/tdd/test_rv32_stage4_trace_runtime.sh
scripts/tdd/test_rv32_stage4_bootstrap_proof.sh
scripts/tdd/test_rv32_bootstrap_docs_sync.sh
scripts/tdd/test_rv32_bootstrap_closure_contract.sh
"

printf "%s" "$EXPECTED" | sed '/^$/d' | sort > "$TMPDIR/expected.list"
sort "$TMPDIR/scripts.list" > "$TMPDIR/actual.list"
cmp -s "$TMPDIR/expected.list" "$TMPDIR/actual.list" || {
  echo "FAIL: bootstrap closure runner scripts mismatch" >&2
  diff -u "$TMPDIR/expected.list" "$TMPDIR/actual.list" >&2 || true
  exit 1
}

FORBID_PATTERNS="
C3_RUN
synthetic
scaffold
TESTG
scripts/forth0/run_f0.sh
test_rv32_stage20
test_rv32_sha
test_rv32_freertos
run_rv32_service_release
run_rv32_service_release_full
run_external_rv32i_corpus.py
rv32i_mvp_check.py
"

failed=0
while IFS= read -r s; do
  [ "$s" = "scripts/tdd/test_rv32_bootstrap_closure_contract.sh" ] && continue
  [ -f "$s" ] || { echo "FAIL: listed script missing: $s"; failed=1; continue; }
  for p in $FORBID_PATTERNS; do
    if rg -n --fixed-strings "$p" "$s" >/dev/null 2>&1; then
      echo "FAIL: bootstrap closure violation in $s -> references '$p'" >&2
      failed=1
    fi
  done
done < "$TMPDIR/scripts.list"

if [ "$failed" -ne 0 ]; then
  exit 1
fi

echo "OK rv32 bootstrap closure contract"
