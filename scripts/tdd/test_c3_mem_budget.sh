#!/bin/sh
set -eu

MAX_TOK_BYTES="${C3_MEM_MAX_TOK_BYTES:-200000}"
MAX_COMPILE_TICKS="${C3_MEM_MAX_COMPILE_TICKS:-20000000}"
MAX_RUN_TICKS="${C3_MEM_MAX_RUN_TICKS:-20000000}"
MAX_DEGR_PCT="${C3_MEM_MAX_DEGR_PCT:-120}"

run_case() {
  label="$1"
  in_f0="$2"
  tmpdir="tmp/c3_mem_budget/$label"
  LIFE_COMPILE="$MAX_COMPILE_TICKS" LIFE_RUN="$MAX_RUN_TICKS" \
    scripts/forth0/run_f0.sh --in "$in_f0" --dump-testg 24 --keep --tmpdir "$tmpdir" >/dev/null

  tok_bytes="$(wc -c < "$tmpdir/prog.tok")"
  compile_ticks="$(sed -n 's/.*ticks=\([0-9][0-9]*\).*/\1/p' "$tmpdir/compile.stderr" | tail -n 1)"
  run_ticks="$(sed -n 's/.*ticks=\([0-9][0-9]*\).*/\1/p' "$tmpdir/run.stderr" | tail -n 1)"

  [ "$tok_bytes" -le "$MAX_TOK_BYTES" ] || { echo "FAIL c3 mem budget: $label tok_bytes=$tok_bytes > $MAX_TOK_BYTES" >&2; exit 1; }
  [ "$compile_ticks" -le "$MAX_COMPILE_TICKS" ] || { echo "FAIL c3 mem budget: $label compile_ticks=$compile_ticks > $MAX_COMPILE_TICKS" >&2; exit 1; }
  [ "$run_ticks" -le "$MAX_RUN_TICKS" ] || { echo "FAIL c3 mem budget: $label run_ticks=$run_ticks > $MAX_RUN_TICKS" >&2; exit 1; }

  echo "$tok_bytes $compile_ticks $run_ticks"
}

mkdir -p tmp/c3_mem_budget

ok_vals="$(run_case ok src/forth0/tests/test_c3_mem_sw_lw_native.f0)"
al_vals="$(run_case align src/forth0/tests/test_c3_mem_align_fault.f0)"

ok_tok="$(echo "$ok_vals" | awk '{print $1}')"
ok_comp="$(echo "$ok_vals" | awk '{print $2}')"
ok_run="$(echo "$ok_vals" | awk '{print $3}')"

al_tok="$(echo "$al_vals" | awk '{print $1}')"
al_comp="$(echo "$al_vals" | awk '{print $2}')"
al_run="$(echo "$al_vals" | awk '{print $3}')"

pct() {
  base="$1"; cur="$2"
  if [ "$base" -le 0 ]; then echo 0; else echo $(( (cur * 100 + base - 1) / base )); fi
}

p_tok="$(pct "$ok_tok" "$al_tok")"
p_comp="$(pct "$ok_comp" "$al_comp")"
p_run="$(pct "$ok_run" "$al_run")"

[ "$p_tok" -le "$MAX_DEGR_PCT" ] || { echo "FAIL c3 mem budget degradation tok=${p_tok}% > ${MAX_DEGR_PCT}%" >&2; exit 1; }
[ "$p_comp" -le "$MAX_DEGR_PCT" ] || { echo "FAIL c3 mem budget degradation compile=${p_comp}% > ${MAX_DEGR_PCT}%" >&2; exit 1; }
[ "$p_run" -le "$MAX_DEGR_PCT" ] || { echo "FAIL c3 mem budget degradation run=${p_run}% > ${MAX_DEGR_PCT}%" >&2; exit 1; }

echo "OK c3 mem budget: ok_tok=$ok_tok ok_comp=$ok_comp ok_run=$ok_run"
