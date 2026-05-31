#!/bin/bash
# Stage 3: Run RISC-V on Copy-Space via existing toolchain

set -e

echo "=== Building base image ==="
make bins || true

echo "=== Compiling riscv.f0 ==="
build/bin/forth0c --image build/std7.bin --in riscv-port/riscv.f0 --out riscv-port/riscv.tok 2>/dev/null || echo "Forth0 compilation would need full decoder implementation"

echo "=== Demo: Python emulator (current working version) ==="
python3 riscv-port/riscv_emulator.py

echo "Done. Full integration requires completing the Forth0 decoder."