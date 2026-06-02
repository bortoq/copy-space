#!/bin/sh
set -eu
MAX_TOK_BYTES="${C3_M_DIV4_MAX_TOK_BYTES:-260000}"
MAX_COMPILE_TICKS="${C3_M_DIV4_MAX_COMPILE_TICKS:-20000000}"
MAX_RUN_TICKS="${C3_M_DIV4_MAX_RUN_TICKS:-20000000}"

tmpdir="tmp/c3_m_div4_budget/native"
LIFE_COMPILE="$MAX_COMPILE_TICKS" LIFE_RUN="$MAX_RUN_TICKS" \
  scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_m_div4.f0 --dump-testg 52 --keep --tmpdir "$tmpdir" >/dev/null

tok_bytes="$(wc -c < "$tmpdir/prog.tok")"
compile_ticks="$(sed -n 's/.*ticks=\([0-9][0-9]*\).*/\1/p' "$tmpdir/compile.stderr" | tail -n 1)"
run_ticks="$(sed -n 's/.*ticks=\([0-9][0-9]*\).*/\1/p' "$tmpdir/run.stderr" | tail -n 1)"

[ "$tok_bytes" -le "$MAX_TOK_BYTES" ] || { echo "FAIL c3 m div4 budget tok=$tok_bytes" >&2; exit 1; }
[ "$compile_ticks" -le "$MAX_COMPILE_TICKS" ] || { echo "FAIL c3 m div4 budget compile=$compile_ticks" >&2; exit 1; }
[ "$run_ticks" -le "$MAX_RUN_TICKS" ] || { echo "FAIL c3 m div4 budget run=$run_ticks" >&2; exit 1; }

echo "OK c3 m div4 budget: tok=$tok_bytes compile=$compile_ticks run=$run_ticks"
