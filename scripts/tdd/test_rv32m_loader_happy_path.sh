#!/bin/sh
# test_rv32m_loader_happy_path.sh — verify loader can load and run a valid image (7.2)
set -eu

BUILDER="scripts/riscv/rv32m_image_builder.py"
LOADER_TOOL="build/bin/rv32m_loader_tool"
TMPDIR="$(mktemp -d tmp/rv32m_loader_happy.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== 7.2 Loader Happy Path ==="

# Create a halt payload
python3 -c "
import struct
def w24(v): return struct.pack('>I', v)[1:]
payload = bytearray(576)
# Slot 0: copy 1 bit from payload byte 575 MSB to halt reg (bit 4759)
payload[0:3] = w24(1)
payload[3:6] = w24(4759)
payload[6:9] = w24(4600)
payload[575] = 0x80
import sys; sys.stdout.buffer.write(payload)
" > "$TMPDIR/halt_payload.bin"

# Build RV32M image
python3 "$BUILDER" build --payload "$TMPDIR/halt_payload.bin" \
  --output "$TMPDIR/test.rv32m" --entry 0 --processor-bits 4608

# Build base space image
build/bin/mkimage_std7_fixed --out "$TMPDIR/base.bin" 2>/dev/null

# Load into space
"$LOADER_TOOL" --rv32m "$TMPDIR/test.rv32m" --space "$TMPDIR/base.bin" \
  --output "$TMPDIR/loaded.bin" 2>&1

# Run and verify VM halts
OUTPUT=$(build/bin/vmrun --image "$TMPDIR/loaded.bin" --life 10000 2>&1)
echo "$OUTPUT"
echo "$OUTPUT" | grep -q "VM halted" || { echo "FAIL: expected VM halt"; exit 1; }

echo "OK: loader happy path passed"
