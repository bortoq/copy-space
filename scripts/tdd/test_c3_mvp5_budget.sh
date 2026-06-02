#!/bin/sh
set -eu

MAX_TOK_BYTES="${C3_MVP5_MAX_TOK_BYTES:-300000}"
MAX_COMPILE_TICKS="${C3_MVP5_MAX_COMPILE_TICKS:-20000000}"
MAX_RUN_TICKS="${C3_MVP5_MAX_RUN_TICKS:-20000000}"
MAX_DEGR_PCT="${C3_MVP5_MAX_DEGR_PCT:-120}"

run_case() {
  mode="$1"
  in_f0="$2"
  tmpdir="tmp/c3_budget/$mode"
  LIFE_COMPILE="$MAX_COMPILE_TICKS" LIFE_RUN="$MAX_RUN_TICKS" \
    scripts/forth0/run_f0.sh --in "$in_f0" --dump-testg 37 --keep --tmpdir "$tmpdir" >/dev/null

  tok_bytes="$(wc -c < "$tmpdir/prog.tok")"
  compile_ticks="$(sed -n 's/.*ticks=\([0-9][0-9]*\).*/\1/p' "$tmpdir/compile.stderr" | tail -n 1)"
  run_ticks="$(sed -n 's/.*ticks=\([0-9][0-9]*\).*/\1/p' "$tmpdir/run.stderr" | tail -n 1)"

  test -n "$compile_ticks"
  test -n "$run_ticks"

  [ "$tok_bytes" -le "$MAX_TOK_BYTES" ] || { echo "FAIL c3 budget: $mode tok_bytes=$tok_bytes > $MAX_TOK_BYTES" >&2; exit 1; }
  [ "$compile_ticks" -le "$MAX_COMPILE_TICKS" ] || { echo "FAIL c3 budget: $mode compile_ticks=$compile_ticks > $MAX_COMPILE_TICKS" >&2; exit 1; }
  [ "$run_ticks" -le "$MAX_RUN_TICKS" ] || { echo "FAIL c3 budget: $mode run_ticks=$run_ticks > $MAX_RUN_TICKS" >&2; exit 1; }

  echo "$tok_bytes $compile_ticks $run_ticks"
}

mkdir -p tmp/c3_budget

scaffold_vals="$(run_case scaffold src/forth0/tests/test_c3_exec_mvp5.f0)"
native_vals="$(run_case native src/forth0/tests/test_c3_exec_mvp5_native_stub.f0)"

s_tok="$(echo "$scaffold_vals" | awk '{print $1}')"
s_comp="$(echo "$scaffold_vals" | awk '{print $2}')"
s_run="$(echo "$scaffold_vals" | awk '{print $3}')"

n_tok="$(echo "$native_vals" | awk '{print $1}')"
n_comp="$(echo "$native_vals" | awk '{print $2}')"
n_run="$(echo "$native_vals" | awk '{print $3}')"

pct() {
  base="$1"
  cur="$2"
  if [ "$base" -le 0 ]; then
    echo 0
  else
    echo $(( (cur * 100 + base - 1) / base ))
  fi
}

tok_pct="$(pct "$s_tok" "$n_tok")"
comp_pct="$(pct "$s_comp" "$n_comp")"
run_pct="$(pct "$s_run" "$n_run")"

[ "$tok_pct" -le "$MAX_DEGR_PCT" ] || { echo "FAIL c3 budget degradation: tok ${tok_pct}% > ${MAX_DEGR_PCT}%" >&2; exit 1; }
[ "$comp_pct" -le "$MAX_DEGR_PCT" ] || { echo "FAIL c3 budget degradation: compile ${comp_pct}% > ${MAX_DEGR_PCT}%" >&2; exit 1; }
[ "$run_pct" -le "$MAX_DEGR_PCT" ] || { echo "FAIL c3 budget degradation: run ${run_pct}% > ${MAX_DEGR_PCT}%" >&2; exit 1; }

echo "OK c3 mvp5 budget: tok=${n_tok}(${tok_pct}%) compile=${n_comp}(${comp_pct}%) run=${n_run}(${run_pct}%)"
