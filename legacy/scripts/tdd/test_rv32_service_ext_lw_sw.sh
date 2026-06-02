#!/bin/sh
set -eu
python3 scripts/riscv/rv32i_mvp_check.py --binary third_party/riscv-external/riscv-tests/rv32ui-p-lw.bin --binary-required --max-instr 16 --outdir tmp/rv32_ext_lw --require lw >/dev/null
echo "OK rv32 service ext lw/sw"
