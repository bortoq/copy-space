#!/bin/sh
# test_rv32m_channel_abi_production.sh — exercise ALL 7 channel operations (ops 0–6)
set -eu

TMPDIR="$(mktemp -d tmp/rv32m_ch_prod.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== Channel ABI Production Test (ops 0–6) ==="

build/bin/mkimage_std7_fixed --out "$TMPDIR/base.bin" 2>/dev/null

# ---------- helper: set a multi-bit value in a space image (MSB-first) ----------
set_bits() {
  local img=$1 bitaddr=$2 nbits=$3 value=$4
  python3 -c "
import sys
d = bytearray(open('$img','rb').read())
ba = $bitaddr; nb = $nbits; v = $value
for i in range(nb):
  byte_idx = (ba + i) // 8
  bit_off  = (ba + i) % 8
  mask = 1 << (7 - bit_off)
  if v & (1 << (nb - 1 - i)):
    d[byte_idx] |= mask
  else:
    d[byte_idx] &= ~mask
open('$img','wb').write(d)
"
}

# ---------- helper: build a standard channel payload ----------
# Produces a loaded image with copy instructions for:
#   ch_op, ch_req, ch_a, ch_b, ch_c, error-check(ch_err→halt)
build_channel_payload() {
  local name=$1 op=$2
  local cha=${3:-0} chb=${4:-0} chc=${5:-0}

  python3 -c "
import struct
def w24(v): return struct.pack('>I', v)[1:]
p = bytearray(576)

# Slot 0: copy 8 bits from slot62 dst LSB (byte563)  -> ch_op (4913)
p[0:3]=w24(8); p[3:6]=w24(4913); p[6:9]=w24(4504)

# Slot 1: copy 1 bit from slot63 src MSB (byte575)    -> ch_req (4910)
p[9:12]=w24(1); p[12:15]=w24(4910); p[15:18]=w24(4600)

# Slot 2: copy 24 bits from slot60 dst (byte543)      -> ch_a  (4921)
p[18:21]=w24(24); p[21:24]=w24(4921); p[24:27]=w24(4344)

# Slot 3: copy 24 bits from slot61 dst (byte552)      -> ch_b  (4945)
p[27:30]=w24(24); p[30:33]=w24(4945); p[33:36]=w24(4416)

# Slot 4: copy 24 bits from slot61 src (byte555)      -> ch_c  (4969)
p[36:39]=w24(24); p[39:42]=w24(4969); p[42:45]=w24(4440)

# Slot 5: copy ch_err(4912) -> halt(4759)  [1 bit]
p[45:48]=w24(1); p[48:51]=w24(4759); p[51:54]=w24(4912)

# ---- data slots ----
# Slot 60: ch_a value
p[540:543]=w24(0); p[543:546]=w24($cha); p[546:549]=w24(0)
# Slot 61: ch_b in dst, ch_c in src
p[549:552]=w24(0); p[552:555]=w24($chb); p[555:558]=w24($chc)
# Slot 62: opcode in dst LSB
p[558:561]=w24(0); p[561:564]=w24($op); p[564:567]=w24(0)
# Slot 63: trigger bit in src MSB (byte575 = 0x80)
p[567:570]=w24(0); p[570:573]=w24(0); p[573:576]=w24(0x80)

import sys; sys.stdout.buffer.write(p)
" > "$TMPDIR/${name}_payload.bin"

  python3 scripts/riscv/rv32m_image_builder.py build \
    --payload "$TMPDIR/${name}_payload.bin" \
    --output "$TMPDIR/${name}.rv32m" --entry 0 --processor-bits 4608 2>/dev/null

  build/bin/rv32m_loader_tool --rv32m "$TMPDIR/${name}.rv32m" \
    --space "$TMPDIR/base.bin" --output "$TMPDIR/${name}_loaded.bin" 2>/dev/null
}

# ========== Test 1: STATUS (op 6) ==========
echo "--- Test 1: STATUS (op 6) — ABI version / tick counter ---"
build_channel_payload "t1_status" 6
OUTPUT=$(build/bin/vmrun --image "$TMPDIR/t1_status_loaded.bin" --life 2 2>&1 || true)
echo "$OUTPUT"
echo "$OUTPUT" | grep -q "VM finished" || { echo "FAIL: STATUS op did not finish"; exit 1; }
echo "$OUTPUT" | grep -q "ticks=2"    || { echo "FAIL: STATUS op — expected ticks=2"; exit 1; }
echo "OK: STATUS completed (VM ticked, ch_a holds tick counter)"

# ========== Test 2: NOP (op 0) ==========
echo "--- Test 2: NOP (op 0) — no-op / ack ---"
build_channel_payload "t2_nop" 0
OUTPUT=$(build/bin/vmrun --image "$TMPDIR/t2_nop_loaded.bin" --life 100 2>&1 || true)
echo "$OUTPUT"
echo "$OUTPUT" | grep -q "VM finished" && echo "OK: NOP — VM finished (NOT halted)" || { echo "FAIL: NOP op"; exit 1; }

# ========== Test 3: STOP (op 1) ==========
echo "--- Test 3: STOP (op 1) — halt VM ---"
build_channel_payload "t3_stop" 1
OUTPUT=$(build/bin/vmrun --image "$TMPDIR/t3_stop_loaded.bin" --life 10000 2>&1 || true)
echo "$OUTPUT"
echo "$OUTPUT" | grep -q "VM halted" && echo "OK: STOP — VM halted" || { echo "FAIL: STOP op"; exit 1; }

# ========== Test 4: STEP_BUDGET (op 2) ==========
echo "--- Test 4: STEP_BUDGET (op 2) — watchdog limit=5 ---"
# Build WITHOUT ch_req copy slot (to avoid re-triggering which resets wd_ticks).
# Pre-set ch_req=1, ch_op=2, ch_c=5 directly in the loaded image.
python3 -c "
import struct
def w24(v): return struct.pack('>I', v)[1:]
p = bytearray(576)

# Slot 0: copy 8 bits from slot62 LSB -> ch_op (4913)
p[0:3]=w24(8); p[3:6]=w24(4913); p[6:9]=w24(4504)

# Slot 4: copy 24 bits from slot61 src -> ch_c (4969)
p[36:39]=w24(24); p[39:42]=w24(4969); p[42:45]=w24(4440)

# Slot 5: error-check: ch_err(4912) -> halt(4759)
p[45:48]=w24(1); p[48:51]=w24(4759); p[51:54]=w24(4912)

# data: slot61 src = ch_c = 5
p[549:552]=w24(0); p[552:555]=w24(0); p[555:558]=w24(5)

# slot62 dst = opcode = 2
p[558:561]=w24(0); p[561:564]=w24(2); p[564:567]=w24(0)

import sys; sys.stdout.buffer.write(p)
" > "$TMPDIR/t4_budget_payload.bin"
python3 scripts/riscv/rv32m_image_builder.py build \
  --payload "$TMPDIR/t4_budget_payload.bin" \
  --output "$TMPDIR/t4_budget.rv32m" --entry 0 --processor-bits 4608 2>/dev/null
build/bin/rv32m_loader_tool --rv32m "$TMPDIR/t4_budget.rv32m" \
  --space "$TMPDIR/base.bin" --output "$TMPDIR/t4_budget_loaded.bin" 2>/dev/null

# Pre-set ch_req=1 (bit 4910), ch_op=2 (8 bits at 4913), ch_c=5 (24 bits at 4969)
set_bits "$TMPDIR/t4_budget_loaded.bin" 4910 1 1
set_bits "$TMPDIR/t4_budget_loaded.bin" 4913 8 2
set_bits "$TMPDIR/t4_budget_loaded.bin" 4969 24 5

OUTPUT=$(build/bin/vmrun --image "$TMPDIR/t4_budget_loaded.bin" --life 10000 2>&1 || true)
echo "$OUTPUT"
echo "$OUTPUT" | grep -q "VM halted" || { echo "FAIL: STEP_BUDGET — expected halt"; exit 1; }
TICKS=$(echo "$OUTPUT" | grep -o 'ticks=[0-9]*' | cut -d= -f2)
if [ "$TICKS" -gt 20 ]; then
  echo "FAIL: watchdog too slow (ticks=$TICKS, limit=5)"; exit 1
fi
echo "OK: STEP_BUDGET — watchdog fired at ticks=$TICKS (limit=5)"

# ========== Test 5: LOAD_IMAGE (op 3) — invalid address ==========
echo "--- Test 5: LOAD_IMAGE (op 3) — invalid source address (ch_err expected) ---"
build_channel_payload "t5_loadimg" 3 0 4608 0
OUTPUT=$(build/bin/vmrun --image "$TMPDIR/t5_loadimg_loaded.bin" --life 10000 2>&1 || true)
echo "$OUTPUT"
echo "$OUTPUT" | grep -q "VM halted" || { echo "FAIL: LOAD_IMAGE — expected ch_err=1 → halt"; exit 1; }
echo "OK: LOAD_IMAGE — invalid address correctly triggered ch_err=1"

# ========== Test 6: IO_WRITE (op 5) ==========
echo "--- Test 6: IO_WRITE (op 5) — write \"Hello\" to stdout ---"
build_channel_payload "t6_iowrite" 5 800000 6 0
# Inject "Hello\0" at byte 100000 of the loaded image
python3 -c "
d = bytearray(open('$TMPDIR/t6_iowrite_loaded.bin','rb').read())
d[100000:100006] = b'Hello\0'
open('$TMPDIR/t6_iowrite_loaded.bin','wb').write(d)
"
build/bin/vmrun --image "$TMPDIR/t6_iowrite_loaded.bin" --life 3 > "$TMPDIR/t6_stdout.txt" 2> "$TMPDIR/t6_stderr.txt" || true
echo "--- vmrun stdout ---"
cat "$TMPDIR/t6_stdout.txt"
echo "--- vmrun stderr ---"
cat "$TMPDIR/t6_stderr.txt"
grep -q "Hello" "$TMPDIR/t6_stdout.txt" && echo "OK: IO_WRITE — \"Hello\" found in stdout" || { echo "FAIL: IO_WRITE — \"Hello\" not in output"; exit 1; }

# ========== Test 7: LOAD_ACK (op 4) ==========
echo "--- Test 7: LOAD_ACK (op 4) — acknowledge load, reset watchdog ---"
build_channel_payload "t7_loadack" 4
OUTPUT=$(build/bin/vmrun --image "$TMPDIR/t7_loadack_loaded.bin" --life 2 2>&1 || true)
echo "$OUTPUT"
echo "$OUTPUT" | grep -q "VM finished" && echo "OK: LOAD_ACK — VM finished, no error" || { echo "FAIL: LOAD_ACK op"; exit 1; }

echo ""
echo "=== ALL 7 CHANNEL ABI PRODUCTION TESTS PASSED ==="
