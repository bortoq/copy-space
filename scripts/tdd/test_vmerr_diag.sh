#!/bin/sh
set -eu

SPACE_BYTES="${SPACE_BYTES:-524288}"
PROCESSOR_N="${PROCESSOR_N:-64}"

BIN_DIR="build/bin"
OUT_DIR="out"
TMP_DIR="tmp"

VMRUN="$BIN_DIR/vmrun"
MKIMAGE="$BIN_DIR/mkimage_std7_fixed"

BASE_IMG="$OUT_DIR/img_fixed_pool_big.bin"
BAD_IMG="$TMP_DIR/bad_bounds.bin"
LOG="$TMP_DIR/vmerr_diag.log"

mkdir -p "$OUT_DIR" "$TMP_DIR"

test -x "$VMRUN"
test -x "$MKIMAGE"
test -x scripts/tdd/mkbench_bad_bounds.py

# base image only needed as template
if [ ! -f "$BASE_IMG" ]; then
  "$MKIMAGE" --out "$BASE_IMG" --pool-cells 32768 > /dev/null 2>&1
fi

scripts/tdd/mkbench_bad_bounds.py --image "$BASE_IMG" --out "$BAD_IMG" \
  --space-bytes "$SPACE_BYTES" --processor-n "$PROCESSOR_N" \
  2> "$TMP_DIR/mkbad.log"

rm -f "$LOG"

# Expect VM_ERR -> nonzero exit code.
# Capture both stdout and stderr (vmrun may print either).
set +e
"$VMRUN" --image "$BAD_IMG" \
  --space-bytes "$SPACE_BYTES" --processor-n "$PROCESSOR_N" \
  --life 10 < /dev/null > "$LOG" 2>&1
rc=$?
set -e

if [ "$rc" -eq 0 ]; then
  echo "ERROR: vmrun unexpectedly exited 0; expected VM_ERR" >&2
  tail -200 "$LOG" >&2 || true
  exit 1
fi

python3 - <<PY
import re, sys

log_path = "$LOG"
space_bits_expected = int("$SPACE_BYTES") * 8

with open(log_path, "r", encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

# Find first VM_ERR line
vmerr = None
for ln in lines:
    if ln.startswith("VM_ERR:"):
        vmerr = ln
        break

if vmerr is None:
    print("ERROR: no 'VM_ERR:' line found in log", file=sys.stderr)
    print("---- tail ----", file=sys.stderr)
    for ln in lines[-50:]:
        print(ln, file=sys.stderr)
    sys.exit(1)

def get_u(name):
    m = re.search(rf"\b{name}=(\d+)\b", vmerr)
    if not m:
        raise AssertionError(f"missing {name}=... in: {vmerr}")
    return int(m.group(1))

tick = get_u("tick")
slot = get_u("slot")
n    = get_u("n")
dst  = get_u("dst")
src  = get_u("src")
kind = get_u("kind")
space_bits = get_u("space_bits")

# basic sanity: expected space_bits matches configured space-bytes
assert space_bits == space_bits_expected, (space_bits, space_bits_expected)

# our generator uses slot0 and tick0 typically (but do not hard fail on tick/slot if it changes later)
assert tick >= 0 and slot >= 0
assert n > 0

# core invariant: it must really be an out-of-bounds copy
assert dst + n > space_bits or src + n > space_bits, (dst, src, n, space_bits)

# kind should be 1 (src bounds) or 2 (dst bounds)
assert kind in (1,2), kind

print("OK VM_ERR diag:", vmerr)
PY
