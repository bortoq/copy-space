#!/bin/bash
# Build and run minimal BusyBox on Forth0 + Copy-Space

set -e

echo "=== Building Forth0 BusyBox ==="

# Build tools if needed
make -C . bins 2>/dev/null || true

# Compile busybox.f0
echo "Compiling busybox.f0..."
build/bin/forth0c --image build/std7.bin \
    --in riscv-port/busybox.f0 \
    --out riscv-port/busybox.tok 2>&1 || echo "Compilation attempted"

echo ""
echo "=== BusyBox source (Forth0) ==="
cat riscv-port/busybox.f0

echo ""
echo "Done. To run full demo use: scripts/forth0/run_f0.sh --in riscv-port/busybox.f0"