#!/bin/sh
# test_rv32m_e2e_universal_loop.sh — full e2e: code→execution→stop/trap (8.3)
set -eu

TMPDIR="$(mktemp -d tmp/rv32m_e2e_loop.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== 8.3 E2E Universal Loop ==="

build/bin/mkimage_std7_fixed --out "$TMPDIR/base.bin" 2>/dev/null

echo "--- Test 1: halt via slot 0 ---"
python3 -c "
import struct
def w24(v): return struct.pack('>I', v)[1:]
payload = bytearray(576)
payload[0:3] = w24(1); payload[3:6] = w24(4759); payload[6:9] = w24(4600)
payload[575] = 0x80
import sys; sys.stdout.buffer.write(payload)
" > "$TMPDIR/payload1.bin"
python3 scripts/riscv/rv32m_image_builder.py build --payload "$TMPDIR/payload1.bin" \
  --output "$TMPDIR/test1.rv32m" --entry 0 --processor-bits 4608 2>/dev/null
build/bin/rv32m_loader_tool --rv32m "$TMPDIR/test1.rv32m" \
  --space "$TMPDIR/base.bin" --output "$TMPDIR/loaded1.bin" 2>/dev/null
OUTPUT=$(build/bin/vmrun --image "$TMPDIR/loaded1.bin" --life 10000 2>&1 || true)
echo "$OUTPUT" | grep -q "VM halted" && echo "OK: halt e2e" || { echo "FAIL: no halt"; exit 1; }

echo "--- Test 2: negative case — out-of-bounds src (VM error) ---"
python3 -c "
import struct
def w24(v): return struct.pack('>I', v)[1:]
payload = bytearray(576)
# force out-of-bounds src for current VM space_bits
payload[0:3] = w24(1); payload[3:6] = w24(4759); payload[6:9] = w24(0xFFFFFF)
import sys; sys.stdout.buffer.write(payload)
" > "$TMPDIR/payload2.bin"
python3 scripts/riscv/rv32m_image_builder.py build --payload "$TMPDIR/payload2.bin" \
  --output "$TMPDIR/test2.rv32m" --entry 0 --processor-bits 4608 2>/dev/null
build/bin/rv32m_loader_tool --rv32m "$TMPDIR/test2.rv32m" \
  --space "$TMPDIR/base.bin" --output "$TMPDIR/loaded2.bin" 2>/dev/null
OUTPUT=$(build/bin/vmrun --image "$TMPDIR/loaded2.bin" --life 10000 2>&1 || true)
echo "$OUTPUT"
echo "$OUTPUT" | grep -q "VM error" && echo "OK: negative e2e (OOB src → VM error)" || { echo "FAIL: oob no error"; exit 1; }

echo ""
echo "ALL E2E UNIVERSAL LOOP CHECKS PASSED"
