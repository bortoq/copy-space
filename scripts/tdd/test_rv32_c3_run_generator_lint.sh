#!/bin/sh
set -eu

GEN="scripts/riscv/gen_c3_run.py"
OUT="src/mkimage/std7_fixed/words_c3_run.c"
mkdir -p tmp
TMPDIR="$(mktemp -d tmp/rv32_c3_genlint.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

[ -f "$GEN" ] || { echo "FAIL: missing $GEN" >&2; exit 1; }
[ -f "$OUT" ] || { echo "FAIL: missing $OUT" >&2; exit 1; }

python3 "$GEN" > "$TMPDIR/generated.c"

# Ensure committed output is in sync with generator.
cmp -s "$TMPDIR/generated.c" "$OUT" || {
  echo "FAIL: words_c3_run.c is not in sync with generator output" >&2
  exit 1
}

# Stage-23 blocker markers: gate must fail while MVP-only shortcuts remain.
if rg -n "opcode matches ADDI|For MVP \(rd=1\)|skip full increment|write_page_budget" "$OUT" >/dev/null 2>&1; then
  echo "FAIL: MVP shortcut markers still present in words_c3_run.c" >&2
  exit 1
fi

echo "OK rv32 c3_run generator lint"
