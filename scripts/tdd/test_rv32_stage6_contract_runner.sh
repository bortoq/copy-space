#!/bin/sh
set -eu

ROOT="scripts/tdd/run_rv32_stage6_contracts.sh"
[ -f "$ROOT" ] || { echo "FAIL: missing $ROOT"; exit 1; }

TMPDIR="$(mktemp -d tmp/rv32_stage6_contract_runner.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

awk '/^sh scripts\/tdd\// { print $2 }' "$ROOT" > "$TMPDIR/scripts.list"

EXPECTED="
scripts/tdd/run_rv32_bootstrap_closure.sh
scripts/tdd/test_rv32_stage6_docs_sync.sh
scripts/tdd/test_rv32_stage6_roadmap_sync.sh
"

printf "%s" "$EXPECTED" | sed '/^$/d' | sort > "$TMPDIR/expected.list"
sort "$TMPDIR/scripts.list" > "$TMPDIR/actual.list"
cmp -s "$TMPDIR/expected.list" "$TMPDIR/actual.list" || {
  echo "FAIL: stage6 contracts runner scripts mismatch" >&2
  diff -u "$TMPDIR/expected.list" "$TMPDIR/actual.list" >&2 || true
  exit 1
}

echo "OK rv32 stage6 contract runner"
