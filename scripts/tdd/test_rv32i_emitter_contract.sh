#!/bin/sh
set -eu

python3 scripts/riscv/build_wave_a_cases.py >/dev/null

cases="
wave_a_demo
wave_a_lui_logic
wave_a_alu_mix
wave_b_shift_cmp
wave_c_e_mem
wave_d_branch_jump
"

for c in $cases; do
  outdir="tmp/rv32i_contract_$c"
  python3 scripts/riscv/rv32i_mvp_check.py \
    --binary "scripts/riscv/cases/$c.bin" \
    --binary-required \
    --outdir "$outdir" \
    --max-instr 256 \
    --max-f0-lines 50000 >/dev/null

  if rg -n "UNSUPPORTED" "$outdir/program.f0" >/dev/null 2>&1; then
    echo "FAIL: $c contains UNSUPPORTED in generated f0" >&2
    exit 1
  fi

done

echo "OK rv32i emitter contract"
