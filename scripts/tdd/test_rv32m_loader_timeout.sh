#!/bin/sh
# test_rv32m_loader_timeout.sh — verify watchdog timeout works with loader (7.2)
set -eu

TMPDIR="$(mktemp -d tmp/rv32m_loader_timeout.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== 7.2 Loader Timeout (watchdog) ==="

# Build a payload that enables watchdog with short limit (but does NOT directly set halt)
python3 -c "
import struct
def w24(v): return struct.pack('>I', v)[1:]
payload = bytearray(576)

# MMIO register addresses:
#   wd_limit  = 4862 (24 bits)
#   wd_enable = 4860 (1 bit)
#
# Slot 0: copy 24-bit value 5 (wd_limit) from payload byte 568 to wd_limit (4862)
#   n=24, dst=4862, src=4544  (568*8=4544)
# Slot 1: copy 1 bit from payload byte 574 MSB to wd_enable (4860)
#   n=1, dst=4860, src=4592  (574*8=4592)
# Slots 2-63: NOP (all zeros)
#
# DO NOT set halt directly — watchdog will set halt when limit is reached.
#
# Byte 568-570: 24-bit value 5 = 0x00 0x00 0x05
# Byte 574: 0x80 (MSB=1 for wd_enable)

payload[0:3] = w24(24)         # n=24
payload[3:6] = w24(4862)       # dst=wd_limit
payload[6:9] = w24(4544)       # src=payload byte 568

payload[9:12] = w24(1)          # n=1
payload[12:15] = w24(4860)      # dst=wd_enable
payload[15:18] = w24(4592)      # src=payload byte 574 MSB

# Data area (well past the processor area within our 576-byte payload)
payload[568:571] = bytes([0x00, 0x00, 0x05])  # wd_limit = 5
payload[574] = 0x80  # MSB=1

import sys; sys.stdout.buffer.write(payload)
" > "$TMPDIR/wd_payload.bin"

python3 scripts/riscv/rv32m_image_builder.py build \
  --payload "$TMPDIR/wd_payload.bin" \
  --output "$TMPDIR/wd_test.rv32m" \
  --entry 0 --processor-bits 4608 2>/dev/null

build/bin/mkimage_std7_fixed --out "$TMPDIR/base.bin" 2>/dev/null
build/bin/rv32m_loader_tool --rv32m "$TMPDIR/wd_test.rv32m" \
  --space "$TMPDIR/base.bin" --output "$TMPDIR/loaded.bin" 2>/dev/null

OUTPUT=$(build/bin/vmrun --image "$TMPDIR/loaded.bin" --life 1000 2>&1)
echo "$OUTPUT"

echo "$OUTPUT" | grep -q "VM halted" || { echo "FAIL: expected VM halt from watchdog"; exit 1; }

TICKS=$(echo "$OUTPUT" | grep -o 'ticks=[0-9]*' | cut -d= -f2)
# Expected: setup takes 2 ticks (tick 0: execute sets wd_enable; tick 1: watchdog starts counting)
# Then watchdog counts 1 per tick, fires after 5 increments.
# So total: ~7-8 ticks.
if [ "$TICKS" -gt 15 ]; then
  echo "FAIL: watchdog did not fire early (ticks=$TICKS)"; exit 1
fi
echo "OK: watchdog fired at ticks=$TICKS (budget=5)"

echo "Loader timeout checks passed"
