#!/bin/sh
set -eu

# Staged plan executor (Wave A baseline + step-trace artifacts + budget gates)

OUT_ROOT="${1:-tmp/rv32i_staged}"
MAX_INSTR="${MAX_INSTR:-256}"
MAX_F0_LINES="${MAX_F0_LINES:-20000}"
MAX_TOK_BYTES="${MAX_TOK_BYTES:-1500000}"
REPEAT_RUNS="${REPEAT_RUNS:-3}"
MAX_COMPILE_TICKS="${MAX_COMPILE_TICKS:-60000000}"
MAX_RUN_TICKS="${MAX_RUN_TICKS:-20000000}"

mkdir -p "$OUT_ROOT"

python3 scripts/riscv/build_wave_a_cases.py >/dev/null

run_case() {
  name="$1"
  bin="$2"
  req="$3"
  outdir="$OUT_ROOT/$name"

  i=1
  digest_ref=""
  while [ "$i" -le "$REPEAT_RUNS" ]; do
    run_dir="$outdir/run_$i"
    # shellcheck disable=SC2086
    python3 scripts/riscv/rv32i_mvp_check.py \
      --binary "$bin" \
      --binary-required \
      --outdir "$run_dir" \
      --max-instr "$MAX_INSTR" \
      --max-f0-lines "$MAX_F0_LINES" \
      $req >/dev/null

    digest="$(python3 - "$run_dir/summary.json" << 'PY'
import json, sys
s = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
print(s['trace_sha256'])
PY
)"
    if [ -z "$digest_ref" ]; then
      digest_ref="$digest"
    elif [ "$digest_ref" != "$digest" ]; then
      echo "FAIL: $name non-deterministic trace digest: ref=$digest_ref run$i=$digest" >&2
      exit 1
    fi
    i=$((i + 1))
  done

  cp "$outdir/run_1/program.f0" "$outdir/program.f0"
  cp "$outdir/run_1/trace.json" "$outdir/trace.json"
  cp "$outdir/run_1/summary.json" "$outdir/summary.json"

  f0tmp="$outdir/f0run"
  LIFE_COMPILE="$MAX_COMPILE_TICKS" LIFE_RUN="$MAX_RUN_TICKS" \
    scripts/forth0/run_f0.sh --in "$outdir/program.f0" --keep --tmpdir "$f0tmp" >/dev/null
  tok_bytes="$(wc -c < "$f0tmp/prog.tok")"
  if [ "$tok_bytes" -gt "$MAX_TOK_BYTES" ]; then
    echo "FAIL: $name tok_bytes=$tok_bytes > budget=$MAX_TOK_BYTES" >&2
    exit 1
  fi

  compile_ticks="$(sed -n 's/.*ticks=\([0-9][0-9]*\).*/\1/p' "$f0tmp/compile.stderr" 2>/dev/null | tail -n 1)"
  run_ticks="$(sed -n 's/.*ticks=\([0-9][0-9]*\).*/\1/p' "$f0tmp/run.stderr" 2>/dev/null | tail -n 1)"
  if [ -z "$run_ticks" ]; then
    run_ticks="$(sed -n 's/.*ticks=\([0-9][0-9]*\).*/\1/p' "$f0tmp/exec.stderr" 2>/dev/null | tail -n 1)"
  fi
  test -n "$compile_ticks" || { echo "FAIL: $name cannot parse compile ticks" >&2; exit 1; }
  test -n "$run_ticks" || { echo "FAIL: $name cannot parse run ticks" >&2; exit 1; }
  if [ "$compile_ticks" -gt "$MAX_COMPILE_TICKS" ]; then
    echo "FAIL: $name compile_ticks=$compile_ticks > budget=$MAX_COMPILE_TICKS" >&2
    exit 1
  fi
  if [ "$run_ticks" -gt "$MAX_RUN_TICKS" ]; then
    echo "FAIL: $name run_ticks=$run_ticks > budget=$MAX_RUN_TICKS" >&2
    exit 1
  fi

  python3 - "$outdir" "$tok_bytes" "$compile_ticks" "$run_ticks" << 'PY'
import json
import sys
from pathlib import Path

outdir = Path(sys.argv[1])
tok_bytes = int(sys.argv[2])
compile_ticks = int(sys.argv[3])
run_ticks = int(sys.argv[4])
summary = json.loads((outdir / "summary.json").read_text(encoding="utf-8"))
summary["tok_bytes"] = tok_bytes
summary["compile_ticks"] = compile_ticks
summary["run_ticks"] = run_ticks
summary["repeat_runs"] = int(__import__("os").environ.get("REPEAT_RUNS", "3"))
(outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"OK {outdir.name}: trace_len={summary['trace_len']} f0_lines={summary['f0_lines']} tok_bytes={tok_bytes} compile_ticks={compile_ticks} run_ticks={run_ticks}")
PY
}

run_case "wave_a_demo" "scripts/riscv/cases/wave_a_demo.bin" "--require addi --require add --require sw"
run_case "wave_a_lui_logic" "scripts/riscv/cases/wave_a_lui_logic.bin" "--require lui --require ori --require andi"
run_case "wave_a_alu_mix" "scripts/riscv/cases/wave_a_alu_mix.bin" "--require addi --require sub --require xor --require or --require and"
run_case "wave_b_shift_cmp" "scripts/riscv/cases/wave_b_shift_cmp.bin" "--require sll --require srl --require sra --require slt --require sltu --require slti --require sltiu"
run_case "wave_c_e_mem" "scripts/riscv/cases/wave_c_e_mem.bin" "--require sb --require sh --require lb --require lbu --require lh --require lhu --require sw --require lw"
run_case "wave_d_branch_jump" "scripts/riscv/cases/wave_d_branch_jump.bin" "--require beq --require bne --require blt --require auipc --require jal --require jalr"
run_case "wave_mvp_compute" "scripts/riscv/cases/wave_mvp_compute.bin" "--require addi --require add --require blt --require sw"
run_case "wave_edge_sign_branch" "scripts/riscv/cases/wave_edge_sign_branch.bin" "--require sb --require lb --require lbu --require bltu"
run_case "wave_branch_bge" "scripts/riscv/cases/wave_branch_bge.bin" "--require bge"
run_case "wave_branch_bgeu" "scripts/riscv/cases/wave_branch_bgeu.bin" "--require bgeu"
run_case "wave_jump_jal_link" "scripts/riscv/cases/wave_jump_jal_link.bin" "--require jal"
run_case "wave_mem_signed_half" "scripts/riscv/cases/wave_mem_signed_half.bin" "--require sh --require lh --require lhu"

echo "STAGED_PLAN_OK out=$OUT_ROOT"
