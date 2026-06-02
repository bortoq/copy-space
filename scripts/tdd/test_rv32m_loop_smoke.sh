#!/bin/sh
# test_rv32m_loop_smoke.sh — basic loop smoke test (8.1)
set -eu

TMPDIR="$(mktemp -d tmp/rv32m_loop_smoke.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== 8.1 Loop Smoke Test ==="

# Build a payload that does a sequence of operations and halts.
# Slot 0: copy 24-bit val 4759 (halt addr) from data to load_src (just for show)
# Actually, let's just verify the VM runs a simple NOP loop and life-exhausts correctly.

# Payload with only NOPs (all zeros) - should run until life exhausted
python3 -c "import sys; sys.stdout.buffer.write(b'\x00'*(4608//8))" > "$TMPDIR/nop_payload.bin"

python3 scripts/riscv/rv32m_image_builder.py build \
  --payload "$TMPDIR/nop_payload.bin" \
  --output "$TMPDIR/nop.rv32m" --entry 0 --processor-bits 4608 2>/dev/null

build/bin/mkimage_std7_fixed --out "$TMPDIR/base.bin" 2>/dev/null
build/bin/rv32m_loader_tool --rv32m "$TMPDIR/nop.rv32m" \
  --space "$TMPDIR/base.bin" --output "$TMPDIR/loaded.bin" 2>/dev/null

OUTPUT=$(build/bin/vmrun --image "$TMPDIR/loaded.bin" --life 50 2>&1)
echo "$OUTPUT"
echo "$OUTPUT" | grep -q "VM finished" || { echo "FAIL: expected life exhausted"; exit 1; }
echo "OK: NOP loop executed 50 ticks"

# Test 2: HALT via payload
python3 -c "
import struct
def w24(v): return struct.pack('>I', v)[1:]
payload = bytearray(576)
# Slot 0: copy 1 bit from byte 575 MSB to halt (4759)
payload[0:3] = w24(1); payload[3:6] = w24(4759); payload[6:9] = w24(4600)
payload[575] = 0x80
import sys; sys.stdout.buffer.write(payload)
" > "$TMPDIR/halt_payload.bin"

python3 scripts/riscv/rv32m_image_builder.py build \
  --payload "$TMPDIR/halt_payload.bin" \
  --output "$TMPDIR/halt.rv32m" --entry 0 --processor-bits 4608 2>/dev/null

build/bin/rv32m_loader_tool --rv32m "$TMPDIR/halt.rv32m" \
  --space "$TMPDIR/base.bin" --output "$TMPDIR/halt_loaded.bin" 2>/dev/null

OUTPUT=$(build/bin/vmrun --image "$TMPDIR/halt_loaded.bin" --life 10000 2>&1)
echo "$OUTPUT" | grep -q "VM halted" || { echo "FAIL: expected halt"; exit 1; }
echo "OK: HALT via direct payload"

echo ""
echo "ALL LOOP SMOKE CHECKS PASSED"
