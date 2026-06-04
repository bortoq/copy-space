#!/bin/sh
set -eu

DOC="doc/rv32_c3_dispatch_contract.md"
GEN="scripts/riscv/gen_c3_run.py"
OUT="src/mkimage/std7_fixed/words_c3_run.c"

[ -f "$DOC" ] || { echo "FAIL: missing $DOC" >&2; exit 1; }
[ -f "$GEN" ] || { echo "FAIL: missing $GEN" >&2; exit 1; }
[ -f "$OUT" ] || { echo "FAIL: missing $OUT" >&2; exit 1; }

rg -n "opcode|funct3|funct7|reject/trap|in sync" "$DOC" >/dev/null

mkdir -p tmp
TMPDIR="$(mktemp -d tmp/rv32_c3_dispatch_contract.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT
python3 "$GEN" > "$TMPDIR/generated.c"
cmp -s "$TMPDIR/generated.c" "$OUT" || {
  echo "FAIL: generated C3_RUN output is not synced with generator" >&2
  exit 1
}

echo "OK rv32 c3 dispatch contract"
