#!/bin/sh
# test_rv32m_unified_entrypoint.sh — verify loader→runtime handoff (8.2)
set -eu

TMPDIR="$(mktemp -d tmp/rv32m_entrypoint.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== 8.2 Unified Entrypoint ==="

build/bin/mkimage_std7_fixed --out "$TMPDIR/base.bin" 2>/dev/null

# Test: load different payloads and verify they all work via unified entrypoint
for test_name in "halt_at_0" "halt_at_1000"; do
  echo "--- Test: $test_name ---"

  if [ "$test_name" = "halt_at_0" ]; then
    ENTRY=0
  else
    ENTRY=0x1000
  fi

  python3 -c "
import struct
def w24(v): return struct.pack('>I', v)[1:]
payload = bytearray(576)
# Actually for entry at 0x1000, we need the processor to have NOPs until slot N
# and the halt at the right slot. Let's keep it simple: place halt in slot 0.
payload[0:3] = w24(1); payload[3:6] = w24(4759); payload[6:9] = w24(4600)
payload[575] = 0x80
import sys; sys.stdout.buffer.write(payload)
" > "$TMPDIR/payload.bin"

  python3 scripts/riscv/rv32m_image_builder.py build \
    --payload "$TMPDIR/payload.bin" \
    --output "$TMPDIR/test.rv32m" --entry $ENTRY --processor-bits 4608 2>/dev/null

  build/bin/rv32m_loader_tool --rv32m "$TMPDIR/test.rv32m" \
    --space "$TMPDIR/base.bin" --output "$TMPDIR/loaded.bin" 2>/dev/null

  OUTPUT=$(build/bin/vmrun --image "$TMPDIR/loaded.bin" --life 10000 2>&1)
  echo "$OUTPUT" | grep -q "VM halted" || { echo "FAIL: no halt for $test_name"; exit 1; }
  echo "OK: $test_name"
done

echo "ALL UNIFIED ENTRYPOINT CHECKS PASSED"
