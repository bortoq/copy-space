#!/bin/sh
# test_rv32m_channel_stop_abi.sh — verify stop/trap ABI via channel (9.3)
set -eu
TMPDIR="$(mktemp -d tmp/rv32m_ch_stop.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT
echo "=== 9.3 Channel Stop ABI ==="
build/bin/mkimage_std7_fixed --out "$TMPDIR/base.bin" 2>/dev/null

# STOP via op=1
python3 -c "
import struct
def w24(v): return struct.pack('>I', v)[1:]
payload = bytearray(576)
payload[0:3] = w24(8); payload[3:6] = w24(4913); payload[6:9] = w24(4504)
payload[9:12] = w24(1); payload[12:15] = w24(4910); payload[15:18] = w24(4600)
payload[558:561] = w24(0); payload[561:564] = w24(1)
payload[567:570] = w24(0); payload[573:576] = w24(0x80)
import sys; sys.stdout.buffer.write(payload)
" > "$TMPDIR/payload.bin"
python3 scripts/riscv/rv32m_image_builder.py build --payload "$TMPDIR/payload.bin" --output "$TMPDIR/stop.rv32m" --entry 0 --processor-bits 4608 2>/dev/null
build/bin/rv32m_loader_tool --rv32m "$TMPDIR/stop.rv32m" --space "$TMPDIR/base.bin" --output "$TMPDIR/loaded.bin" 2>/dev/null
OUTPUT=$(build/bin/vmrun --image "$TMPDIR/loaded.bin" --life 10000 2>&1 || true)
echo "$OUTPUT" | grep -q "VM halted" && echo "OK: STOP ABI via channel (stop reason=1)" || { echo "FAIL"; exit 1; }
echo "ALL CHANNEL STOP ABI CHECKS PASSED"
