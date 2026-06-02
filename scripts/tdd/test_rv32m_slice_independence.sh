#!/bin/sh
# test_rv32m_slice_independence.sh — verify execution without curated slices (8.2)
set -eu

TMPDIR="$(mktemp -d tmp/rv32m_slice_indep.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== 8.2 Slice Independence ==="

# Create a payload directly (no Forth0, no C3 slices needed)
# The payload is pure copy instructions that set halt
python3 -c "
import struct
def w24(v): return struct.pack('>I', v)[1:]
payload = bytearray(576)
# Halt in slot 0
payload[0:3] = w24(1); payload[3:6] = w24(4759); payload[6:9] = w24(4600)
payload[575] = 0x80
import sys; sys.stdout.buffer.write(payload)
" > "$TMPDIR/direct_payload.bin"

# Build image directly (no Forth0 compilation needed)
python3 scripts/riscv/rv32m_image_builder.py build \
  --payload "$TMPDIR/direct_payload.bin" \
  --output "$TMPDIR/direct.rv32m" --entry 0 --processor-bits 4608 2>/dev/null

# Load and run against a correctly-sized base image.
# (Size must match current VM build defaults.)
build/bin/mkimage_std7_fixed --out "$TMPDIR/base.bin" 2>/dev/null

build/bin/rv32m_loader_tool --rv32m "$TMPDIR/direct.rv32m" \
  --space "$TMPDIR/base.bin" --output "$TMPDIR/loaded.bin" 2>/dev/null

OUTPUT=$(build/bin/vmrun --image "$TMPDIR/loaded.bin" --life 10000 2>&1)
echo "$OUTPUT"
echo "$OUTPUT" | grep -q "VM halted" || { echo "FAIL: slice-independent execution failed"; exit 1; }

echo "OK: slice-independent payload executed (no Forth0/curated slices)"
echo "ALL SLICE INDEPENDENCE CHECKS PASSED"
