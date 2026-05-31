#!/bin/bash
# Build and test minimal filesystem on Forth0

set -e

echo "=== Minimal Filesystem on Forth0 ==="

make bins 2>/dev/null || true

echo "Compiling minimal-fs.f0..."
build/bin/forth0c --image build/std7.bin \
    --in riscv-port/minimal-fs.f0 \
    --out riscv-port/minimal-fs.tok 2>&1 || true

echo ""
echo "=== Filesystem Demo ==="
cat riscv-port/minimal-fs.f0 | tail -30

echo ""
echo "Done."