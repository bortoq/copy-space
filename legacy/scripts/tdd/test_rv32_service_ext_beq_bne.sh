#!/bin/sh
set -eu
python3 scripts/riscv/rv32i_mvp_check.py --binary third_party/riscv-external/riscv-tests/rv32ui-p-beq.bin --binary-required --max-instr 16 --outdir tmp/rv32_ext_beq --require beq >/dev/null
python3 scripts/riscv/rv32i_mvp_check.py --binary third_party/riscv-external/riscv-tests/rv32ui-p-bne.bin --binary-required --max-instr 16 --outdir tmp/rv32_ext_bne --require bne >/dev/null
echo "OK rv32 service ext beq/bne"
