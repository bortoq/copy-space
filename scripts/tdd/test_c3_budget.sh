#!/bin/sh
set -eu

MAX_TOK_MVP5="${C3_MVP5_MAX_TOK_BYTES:-300000}"
MAX_TOK_MEM="${C3_MEM_MAX_TOK_BYTES:-200000}"
MAX_TOK_BRANCH="${C3_BRANCH_MAX_TOK_BYTES:-220000}"
MAX_TOK_SUBWORD="${C3_SUBWORD_MAX_TOK_BYTES:-250000}"

MAX_COMPILE="${C3_S9_MAX_COMPILE_TICKS:-20000000}"
MAX_RUN="${C3_S9_MAX_RUN_TICKS:-20000000}"
MAX_DEGR_PCT="${C3_S9_MAX_DEGR_PCT:-110}"
REPEATS="${C3_S9_REPEATS:-3}"

run_case() {
  case_id="$1"
  in_f0="$2"
  dump_words="$3"
  steps="$4"
  max_tok="$5"
  outdir="$6"

  LIFE_COMPILE="$MAX_COMPILE" LIFE_RUN="$MAX_RUN" \
    scripts/forth0/run_f0.sh --in "$in_f0" --dump-testg "$dump_words" --keep --tmpdir "$outdir" >/dev/null

  tok_bytes="$(wc -c < "$outdir/prog.tok")"
  compile_ticks="$(sed -n 's/.*ticks=\([0-9][0-9]*\).*/\1/p' "$outdir/compile.stderr" | tail -n 1)"
  run_ticks="$(sed -n 's/.*ticks=\([0-9][0-9]*\).*/\1/p' "$outdir/run.stderr" | tail -n 1)"

  test -n "$compile_ticks"
  test -n "$run_ticks"

  [ "$tok_bytes" -le "$max_tok" ] || { echo "FAIL c3 budget($case_id): tok_bytes=$tok_bytes > $max_tok" >&2; exit 1; }
  [ "$compile_ticks" -le "$MAX_COMPILE" ] || { echo "FAIL c3 budget($case_id): compile_ticks=$compile_ticks > $MAX_COMPILE" >&2; exit 1; }
  [ "$run_ticks" -le "$MAX_RUN" ] || { echo "FAIL c3 budget($case_id): run_ticks=$run_ticks > $MAX_RUN" >&2; exit 1; }

  tpk=$(( (run_ticks * 1000 + steps - 1) / steps ))
  echo "$tok_bytes $compile_ticks $run_ticks $tpk"
}

pct() {
  base="$1"
  cur="$2"
  if [ "$base" -le 0 ]; then
    echo 0
  else
    echo $(( (cur * 100 + base - 1) / base ))
  fi
}

mkdir -p tmp/c3_budget_s9

baseline=""
i=1
while [ "$i" -le "$REPEATS" ]; do
  root="tmp/c3_budget_s9/run_$i"
  mkdir -p "$root"

  mvp5="$(run_case mvp5 src/forth0/tests/test_c3_exec_mvp5_native_stub.f0 37 5 "$MAX_TOK_MVP5" "$root/mvp5")"
  mem="$(run_case mem src/forth0/tests/test_c3_mem_sw_lw_native.f0 24 2 "$MAX_TOK_MEM" "$root/mem")"
  branch="$(run_case branch src/forth0/tests/test_c3_branch_matrix.f0 29 6 "$MAX_TOK_BRANCH" "$root/branch")"
  subword="$(run_case subword src/forth0/tests/test_c3_mem_subword.f0 36 6 "$MAX_TOK_SUBWORD" "$root/subword")"

  line="$mvp5 | $mem | $branch | $subword"
  if [ -z "$baseline" ]; then
    baseline="$line"
  else
    b_mvp5="$(echo "$baseline" | awk -F' \| ' '{print $1}')"
    b_mem="$(echo "$baseline" | awk -F' \| ' '{print $2}')"
    b_branch="$(echo "$baseline" | awk -F' \| ' '{print $3}')"
    b_subword="$(echo "$baseline" | awk -F' \| ' '{print $4}')"

    for pair in \
      "mvp5:$b_mvp5:$mvp5" \
      "mem:$b_mem:$mem" \
      "branch:$b_branch:$branch" \
      "subword:$b_subword:$subword"
    do
      case_id="$(echo "$pair" | cut -d: -f1)"
      b_vals="$(echo "$pair" | cut -d: -f2)"
      c_vals="$(echo "$pair" | cut -d: -f3)"

      b_tok="$(echo "$b_vals" | awk '{print $1}')"
      b_comp="$(echo "$b_vals" | awk '{print $2}')"
      b_run="$(echo "$b_vals" | awk '{print $3}')"
      b_tpk="$(echo "$b_vals" | awk '{print $4}')"

      c_tok="$(echo "$c_vals" | awk '{print $1}')"
      c_comp="$(echo "$c_vals" | awk '{print $2}')"
      c_run="$(echo "$c_vals" | awk '{print $3}')"
      c_tpk="$(echo "$c_vals" | awk '{print $4}')"

      p_tok="$(pct "$b_tok" "$c_tok")"
      p_comp="$(pct "$b_comp" "$c_comp")"
      p_run="$(pct "$b_run" "$c_run")"
      p_tpk="$(pct "$b_tpk" "$c_tpk")"

      [ "$p_tok" -le "$MAX_DEGR_PCT" ] || { echo "FAIL c3 budget repeat($case_id): tok ${p_tok}% > ${MAX_DEGR_PCT}%" >&2; exit 1; }
      [ "$p_comp" -le "$MAX_DEGR_PCT" ] || { echo "FAIL c3 budget repeat($case_id): compile ${p_comp}% > ${MAX_DEGR_PCT}%" >&2; exit 1; }
      [ "$p_run" -le "$MAX_DEGR_PCT" ] || { echo "FAIL c3 budget repeat($case_id): run ${p_run}% > ${MAX_DEGR_PCT}%" >&2; exit 1; }
      [ "$p_tpk" -le "$MAX_DEGR_PCT" ] || { echo "FAIL c3 budget repeat($case_id): ticks_per_1k ${p_tpk}% > ${MAX_DEGR_PCT}%" >&2; exit 1; }
    done
  fi

  printf '%s\n' "$line" > "$root/summary.txt"
  i=$((i + 1))
done

# Persist baseline summary from first run.
b_mvp5="$(echo "$baseline" | awk -F' \| ' '{print $1}')"
b_mem="$(echo "$baseline" | awk -F' \| ' '{print $2}')"
b_branch="$(echo "$baseline" | awk -F' \| ' '{print $3}')"
b_subword="$(echo "$baseline" | awk -F' \| ' '{print $4}')"

cat > tmp/c3_budget_s9/baseline.json <<JSON
{
  "mvp5": {"tok_bytes": $(echo "$b_mvp5" | awk '{print $1}'), "compile_ticks": $(echo "$b_mvp5" | awk '{print $2}'), "run_ticks": $(echo "$b_mvp5" | awk '{print $3}'), "ticks_per_1k_steps": $(echo "$b_mvp5" | awk '{print $4}')},
  "mem": {"tok_bytes": $(echo "$b_mem" | awk '{print $1}'), "compile_ticks": $(echo "$b_mem" | awk '{print $2}'), "run_ticks": $(echo "$b_mem" | awk '{print $3}'), "ticks_per_1k_steps": $(echo "$b_mem" | awk '{print $4}')},
  "branch": {"tok_bytes": $(echo "$b_branch" | awk '{print $1}'), "compile_ticks": $(echo "$b_branch" | awk '{print $2}'), "run_ticks": $(echo "$b_branch" | awk '{print $3}'), "ticks_per_1k_steps": $(echo "$b_branch" | awk '{print $4}')},
  "subword": {"tok_bytes": $(echo "$b_subword" | awk '{print $1}'), "compile_ticks": $(echo "$b_subword" | awk '{print $2}'), "run_ticks": $(echo "$b_subword" | awk '{print $3}'), "ticks_per_1k_steps": $(echo "$b_subword" | awk '{print $4}')}
}
JSON

echo "OK c3 budget: repeats=$REPEATS degr<=${MAX_DEGR_PCT}% baseline=tmp/c3_budget_s9/baseline.json"
