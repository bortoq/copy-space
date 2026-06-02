#!/bin/sh
# test_rv32m_loop_stability.sh — runtime stability checks (8.4)
set -eu

TMPDIR="$(mktemp -d tmp/rv32m_stability.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== 8.4 Runtime Stability ==="

build/bin/mkimage_std7_fixed --out "$TMPDIR/base.bin" 2>/dev/null

# Create a halt payload
python3 -c "
import struct
def w24(v): return struct.pack('>I', v)[1:]
payload = bytearray(576)
payload[0:3] = w24(1); payload[3:6] = w24(4759); payload[6:9] = w24(4600)
payload[575] = 0x80
import sys; sys.stdout.buffer.write(payload)
" > "$TMPDIR/payload.bin"
python3 scripts/riscv/rv32m_image_builder.py build --payload "$TMPDIR/payload.bin" \
  --output "$TMPDIR/test.rv32m" --entry 0 --processor-bits 4608 2>/dev/null
build/bin/rv32m_loader_tool --rv32m "$TMPDIR/test.rv32m" \
  --space "$TMPDIR/base.bin" --output "$TMPDIR/loaded.bin" 2>/dev/null

echo "--- 8.4.1: Repeat-stability 3/3 ---"
TICKS1=$(build/bin/vmrun --image "$TMPDIR/loaded.bin" --life 10000 2>&1 | grep -o 'ticks=[0-9]*' | cut -d= -f2)
TICKS2=$(build/bin/vmrun --image "$TMPDIR/loaded.bin" --life 10000 2>&1 | grep -o 'ticks=[0-9]*' | cut -d= -f2)
TICKS3=$(build/bin/vmrun --image "$TMPDIR/loaded.bin" --life 10000 2>&1 | grep -o 'ticks=[0-9]*' | cut -d= -f2)
echo "  run 1: ticks=$TICKS1"
echo "  run 2: ticks=$TICKS2"
echo "  run 3: ticks=$TICKS3"
if [ "$TICKS1" = "$TICKS2" ] && [ "$TICKS2" = "$TICKS3" ]; then
  echo "OK: repeat-stability 3/3 (ticks=$TICKS1)"
else
  echo "FAIL: non-deterministic ticks ($TICKS1 $TICKS2 $TICKS3)"
  exit 1
fi

echo "--- 8.4.2: Budget metrics (ticks < limit) ---"
OUT=$(build/bin/vmrun --image "$TMPDIR/loaded.bin" --life 100 2>&1)
TICKS=$(echo "$OUT" | grep -o 'ticks=[0-9]*' | cut -d= -f2)
if [ "$TICKS" -le 10 ]; then
  echo "OK: budget OK (ticks=$TICKS < 100)"
else
  echo "FAIL: budget exceeded ($TICKS)"
  exit 1
fi

echo ""
echo "ALL RUNTIME STABILITY CHECKS PASSED"
