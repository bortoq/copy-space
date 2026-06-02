#!/bin/sh
set -eu

scripts/riscv/run_staged_plan.sh tmp/rv32i_staged_test >/dev/null

for c in wave_a_demo wave_a_lui_logic wave_a_alu_mix wave_b_shift_cmp wave_c_e_mem wave_d_branch_jump wave_mvp_compute wave_edge_sign_branch wave_branch_bge wave_branch_bgeu wave_jump_jal_link wave_mem_signed_half; do
  test -f "tmp/rv32i_staged_test/$c/program.f0"
  test -f "tmp/rv32i_staged_test/$c/trace.json"
  test -f "tmp/rv32i_staged_test/$c/summary.json"
done

python3 - << 'PY'
import json
from pathlib import Path
root = Path('tmp/rv32i_staged_test')
MAX_COMPILE_TICKS = 60_000_000
MAX_RUN_TICKS = 20_000_000
for case in ('wave_a_demo', 'wave_a_lui_logic', 'wave_a_alu_mix', 'wave_b_shift_cmp', 'wave_c_e_mem', 'wave_d_branch_jump', 'wave_mvp_compute', 'wave_edge_sign_branch', 'wave_branch_bge', 'wave_branch_bgeu', 'wave_jump_jal_link', 'wave_mem_signed_half'):
    s = json.loads((root / case / 'summary.json').read_text(encoding='utf-8'))
    assert s['ok'] is True
    assert s['trace_len'] > 0
    assert s['f0_lines'] > 0
    assert s['tok_bytes'] <= 1_500_000
    assert s['compile_ticks'] <= MAX_COMPILE_TICKS
    assert s['run_ticks'] <= MAX_RUN_TICKS
print('OK staged summaries')
PY
