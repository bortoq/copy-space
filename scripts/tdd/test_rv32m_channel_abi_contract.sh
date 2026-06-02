#!/bin/sh
# test_rv32m_channel_abi_contract.sh — verify channel ABI operations (9.1)
set -eu

TMPDIR="$(mktemp -d tmp/rv32m_ch_abi.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== 9.1 Channel ABI Contract ==="

build/bin/mkimage_std7_fixed --out "$TMPDIR/base.bin" 2>/dev/null

build_channel_payload() {
  local op=$1
  local name=$2
  
  python3 -c "
import struct
def w24(v): return struct.pack('>I', v)[1:]
payload = bytearray(576)

# Slot 0: copy 8 bits from slot62_dst LSB (byte 563) to ch_op (4913)
#   byte 563 * 8 = 4504
payload[0:3] = w24(8); payload[3:6] = w24(4913); payload[6:9] = w24(4504)

# Slot 1: copy 1 bit from slot63_src byte575 MSB (bit 4600) to ch_req (4910)
payload[9:12] = w24(1); payload[12:15] = w24(4910); payload[15:18] = w24(4600)

# DATA in NOP slots:
# Slot 62: n=0 (NOP), dst=$op (opcode in LSB byte)
payload[558:561] = w24(0)        # n=0
payload[561:564] = w24($op)      # dst = opcode (e.g., 1 for STOP)
# Slot 63: n=0 (NOP), set src to have a '1' bit at byte575 MSB
payload[567:570] = w24(0)        # n=0
payload[573:576] = w24(0x80)     # src = [0x00,0x00,0x80], MSB of byte575 = 1

import sys; sys.stdout.buffer.write(payload)
" > "$TMPDIR/${name}_payload.bin"
  
  python3 scripts/riscv/rv32m_image_builder.py build \
    --payload "$TMPDIR/${name}_payload.bin" \
    --output "$TMPDIR/${name}.rv32m" --entry 0 --processor-bits 4608 2>/dev/null
  build/bin/rv32m_loader_tool --rv32m "$TMPDIR/${name}.rv32m" \
    --space "$TMPDIR/base.bin" --output "$TMPDIR/${name}_loaded.bin" 2>/dev/null
}

echo "--- Test 1: op=1 (STOP) should trigger HALT ---"
build_channel_payload 1 "stop"
OUTPUT=$(build/bin/vmrun --image "$TMPDIR/stop_loaded.bin" --life 10000 2>&1 || true)
echo "$OUTPUT" | grep -q "VM halted" && echo "OK: STOP → HALT" || { echo "FAIL: STOP op"; exit 1; }

echo "--- Test 2: op=0 (NOP/ACK) should NOT halt ---"
build_channel_payload 0 "nop"
OUTPUT=$(build/bin/vmrun --image "$TMPDIR/nop_loaded.bin" --life 10000 2>&1 || true)
echo "$OUTPUT" | grep -q "VM finished" && echo "OK: NOP → no halt" || { echo "FAIL: NOP op"; exit 1; }

echo ""
echo "ALL CHANNEL ABI CONTRACT CHECKS PASSED"
