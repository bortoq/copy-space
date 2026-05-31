#!/bin/bash
# Run RISC-V emulation inside Copy-Space using copy instructions

set -e

echo "=== RISC-V in Copy-Space ==="

# 1. Lower RISC-V to copy operations
echo "[1] Lowering RISC-V instructions to copybits..."
python3 riscv-port/riscv_copy_lowering.py > riscv-port/lowered_copies.txt
cat riscv-port/lowered_copies.txt

# 2. Generate simple copy demands CSV (for scheduler)
echo "[2] Generating copy demands CSV..."
cat > riscv-port/riscv_copies.csv << EOF
src,dst,width
reg0,ALU_A,32
imm_42,ALU_B,32
ALU_result,reg1,32
reg1,ALU_A,32
reg2,ALU_B,32
ALU_result,reg3,32
EOF

# 3. Run Copy-Space scheduler on the demands
echo "[3] Running Copy-Space scheduler..."
if command -v copyspace-pilot &> /dev/null; then
    copyspace-pilot --csv riscv-port/riscv_copies.csv --bw 256 --outdir riscv-port/schedule
else
    echo "Note: copyspace-pilot not in PATH. Using python module..."
    python -m copyspace.pilot --csv riscv-port/riscv_copies.csv --bw 256 --outdir riscv-port/schedule || echo "Scheduler run attempted"
fi

echo ""
echo "=== Done ==="
echo "Results in: riscv-port/schedule/"
ls -la riscv-port/schedule/ 2>/dev/null || true