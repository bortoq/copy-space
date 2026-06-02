#!/bin/sh
# test_rv32m_loop_watchdog.sh — verify watchdog bounded-step mode (8.1)
set -eu

TMPDIR="$(mktemp -d tmp/rv32m_loop_wd.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== 8.1 Loop Watchdog ==="

# Build payload that enables watchdog with limit=3
python3 -c "
import struct
def w24(v): return struct.pack('>I', v)[1:]
payload = bytearray(576)
# Slot 0: copy 24-bit val 3 from byte 568 to wd_limit (4862)
payload[0:3] = w24(24); payload[3:6] = w24(4862); payload[6:9] = w24(4544)
# Slot 1: copy 1 bit from byte 574 MSB to wd_enable (4860)
payload[9:12] = w24(1); payload[12:15] = w24(4860); payload[15:18] = w24(4592)
# Data
payload[568:571] = bytes([0x00, 0x00, 0x03])
payload[574] = 0x80
import sys; sys.stdout.buffer.write(payload)
" > "$TMPDIR/wd_payload.bin"

python3 scripts/riscv/rv32m_image_builder.py build \
  --payload "$TMPDIR/wd_payload.bin" \
  --output "$TMPDIR/wd_test.rv32m" --entry 0 --processor-bits 4608 2>/dev/null

build/bin/mkimage_std7_fixed --out "$TMPDIR/base.bin" 2>/dev/null
build/bin/rv32m_loader_tool --rv32m "$TMPDIR/wd_test.rv32m" \
  --space "$TMPDIR/base.bin" --output "$TMPDIR/loaded.bin" 2>/dev/null

OUTPUT=$(build/bin/vmrun --image "$TMPDIR/loaded.bin" --life 1000 2>&1)
echo "$OUTPUT"
echo "$OUTPUT" | grep -q "VM halted" || { echo "FAIL: expected halt"; exit 1; }
TICKS=$(echo "$OUTPUT" | grep -o 'ticks=[0-9]*' | cut -d= -f2)

# With limit=3: tick 0 sets wd_enable, tick 1-3 count, tick 4 fires halt
if [ "$TICKS" -gt 10 ]; then
  echo "FAIL: watchdog too slow (ticks=$TICKS)"; exit 1
fi
echo "OK: watchdog fired at ticks=$TICKS (limit=3)"
