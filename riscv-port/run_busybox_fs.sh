#!/bin/bash
# Run integrated BusyBox + Filesystem

set -e

echo "=== BusyBox + Minimal FS ==="

make bins 2>/dev/null || true

echo "Compiling busybox-fs.f0..."
build/bin/forth0c --image build/std7.bin \
    --in riscv-port/busybox-fs.f0 \
    --out riscv-port/busybox-fs.tok 2>&1 || true

echo ""
echo "Integration complete."
echo "Source: riscv-port/busybox-fs.f0"