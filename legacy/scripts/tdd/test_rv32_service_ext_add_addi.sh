#!/bin/sh
set -eu
python3 scripts/riscv/rv32i_mvp_check.py --binary third_party/riscv-external/riscv-tests/rv32ui-p-addi.bin --binary-required --max-instr 16 --outdir tmp/rv32_ext_addi --require addi >/dev/null
python3 scripts/riscv/rv32i_mvp_check.py --binary third_party/riscv-external/riscv-tests/rv32ui-p-add.bin --binary-required --max-instr 16 --outdir tmp/rv32_ext_add --require add >/dev/null
echo "OK rv32 service ext add/addi"
