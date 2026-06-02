#!/bin/sh
set -eu

MAX_COMPILE="${C3_RV32M_MAX_COMPILE_TICKS:-20000000}"
MAX_RUN="${C3_RV32M_MAX_RUN_TICKS:-20000000}"
MAX_DEGR_PCT="${C3_RV32M_MAX_DEGR_PCT:-110}"
REPEATS="${C3_RV32M_REPEATS:-3}"
MAX_TOK="${C3_RV32M_MAX_TOK_BYTES:-260000}"

pct() {
  base="$1"
  cur="$2"
  if [ "$base" -le 0 ]; then
    echo 0
  else
    echo $(( (cur * 100 + base - 1) / base ))
  fi
}

run_case() {
  case_id="$1"
  in_f0="$2"
  outdir="$3"
  steps=8

  LIFE_COMPILE="$MAX_COMPILE" LIFE_RUN="$MAX_RUN" \
    scripts/forth0/run_f0.sh --in "$in_f0" --dump-testg 52 --keep --tmpdir "$outdir" >/dev/null

  tok_bytes="$(wc -c < "$outdir/prog.tok")"
  compile_ticks="$(sed -n 's/.*ticks=\([0-9][0-9]*\).*/\1/p' "$outdir/compile.stderr" | tail -n 1)"
  run_ticks="$(sed -n 's/.*ticks=\([0-9][0-9]*\).*/\1/p' "$outdir/run.stderr" | tail -n 1)"
  tpk=$(( (run_ticks * 1000 + steps - 1) / steps ))

  [ "$tok_bytes" -le "$MAX_TOK" ] || { echo "FAIL rv32m budget($case_id): tok=$tok_bytes > $MAX_TOK" >&2; exit 1; }
  [ "$compile_ticks" -le "$MAX_COMPILE" ] || { echo "FAIL rv32m budget($case_id): compile=$compile_ticks > $MAX_COMPILE" >&2; exit 1; }
  [ "$run_ticks" -le "$MAX_RUN" ] || { echo "FAIL rv32m budget($case_id): run=$run_ticks > $MAX_RUN" >&2; exit 1; }

  echo "$tok_bytes $compile_ticks $run_ticks $tpk"
}

mkdir -p tmp/c3_rv32m_budget
baseline=""
i=1
while [ "$i" -le "$REPEATS" ]; do
  root="tmp/c3_rv32m_budget/run_$i"
  mkdir -p "$root"

  mul4="$(run_case mul4 src/forth0/tests/test_c3_m_mul4.f0 "$root/mul4")"
  div4="$(run_case div4 src/forth0/tests/test_c3_m_div4.f0 "$root/div4")"
  corner="$(run_case corner src/forth0/tests/test_c3_m_div_corner.f0 "$root/corner")"

  line="$mul4 | $div4 | $corner"

  if [ -z "$baseline" ]; then
    baseline="$line"
  else
    b_mul4="$(echo "$baseline" | awk -F' \| ' '{print $1}')"
    b_div4="$(echo "$baseline" | awk -F' \| ' '{print $2}')"
    b_corner="$(echo "$baseline" | awk -F' \| ' '{print $3}')"

    for pair in "mul4:$b_mul4:$mul4" "div4:$b_div4:$div4" "corner:$b_corner:$corner"; do
      cid="$(echo "$pair" | cut -d: -f1)"
      b_vals="$(echo "$pair" | cut -d: -f2)"
      c_vals="$(echo "$pair" | cut -d: -f3)"

      b_tok="$(echo "$b_vals" | awk '{print $1}')"; c_tok="$(echo "$c_vals" | awk '{print $1}')"
      b_comp="$(echo "$b_vals" | awk '{print $2}')"; c_comp="$(echo "$c_vals" | awk '{print $2}')"
      b_run="$(echo "$b_vals" | awk '{print $3}')"; c_run="$(echo "$c_vals" | awk '{print $3}')"
      b_tpk="$(echo "$b_vals" | awk '{print $4}')"; c_tpk="$(echo "$c_vals" | awk '{print $4}')"

      p_tok="$(pct "$b_tok" "$c_tok")"
      p_comp="$(pct "$b_comp" "$c_comp")"
      p_run="$(pct "$b_run" "$c_run")"
      p_tpk="$(pct "$b_tpk" "$c_tpk")"

      [ "$p_tok" -le "$MAX_DEGR_PCT" ] || { echo "FAIL rv32m repeat($cid): tok ${p_tok}% > ${MAX_DEGR_PCT}%" >&2; exit 1; }
      [ "$p_comp" -le "$MAX_DEGR_PCT" ] || { echo "FAIL rv32m repeat($cid): compile ${p_comp}% > ${MAX_DEGR_PCT}%" >&2; exit 1; }
      [ "$p_run" -le "$MAX_DEGR_PCT" ] || { echo "FAIL rv32m repeat($cid): run ${p_run}% > ${MAX_DEGR_PCT}%" >&2; exit 1; }
      [ "$p_tpk" -le "$MAX_DEGR_PCT" ] || { echo "FAIL rv32m repeat($cid): tpk ${p_tpk}% > ${MAX_DEGR_PCT}%" >&2; exit 1; }
    done
  fi

  printf '%s\n' "$line" > "$root/summary.txt"
  i=$((i + 1))
done

b_mul4="$(echo "$baseline" | awk -F' \| ' '{print $1}')"
b_div4="$(echo "$baseline" | awk -F' \| ' '{print $2}')"
b_corner="$(echo "$baseline" | awk -F' \| ' '{print $3}')"

cat > tmp/c3_rv32m_budget/baseline.json <<JSON
{
  "mul4": {"tok_bytes": $(echo "$b_mul4" | awk '{print $1}'), "compile_ticks": $(echo "$b_mul4" | awk '{print $2}'), "run_ticks": $(echo "$b_mul4" | awk '{print $3}'), "ticks_per_1k_steps": $(echo "$b_mul4" | awk '{print $4}')},
  "div4": {"tok_bytes": $(echo "$b_div4" | awk '{print $1}'), "compile_ticks": $(echo "$b_div4" | awk '{print $2}'), "run_ticks": $(echo "$b_div4" | awk '{print $3}'), "ticks_per_1k_steps": $(echo "$b_div4" | awk '{print $4}')},
  "div_corner": {"tok_bytes": $(echo "$b_corner" | awk '{print $1}'), "compile_ticks": $(echo "$b_corner" | awk '{print $2}'), "run_ticks": $(echo "$b_corner" | awk '{print $3}'), "ticks_per_1k_steps": $(echo "$b_corner" | awk '{print $4}')}
}
JSON

echo "OK c3 rv32m budget freeze: repeats=$REPEATS degr<=${MAX_DEGR_PCT}% baseline=tmp/c3_rv32m_budget/baseline.json"
