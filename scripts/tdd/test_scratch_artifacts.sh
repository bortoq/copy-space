#!/bin/sh
set -eu

OUT_DIR="out"
TMP_DIR="tmp"

IMG="$OUT_DIR/img_fixed_pool_big.bin"
META="$TMP_DIR/mkimage_big.meta"

mkdir -p "$OUT_DIR" "$TMP_DIR"

scripts/mkimage_meta.sh --out "$IMG" --pool-cells 32768 --meta "$META" >/dev/null 2>&1

# shellcheck disable=SC1090
. "$META"

python3 - <<PY
img = "$IMG"
art_b = int("$ART_BYTE")
testscr_base_bit = int("$TESTSCR_BASE_BYTE") * 8
testscr_end_bit  = int("$TESTSCR_END_BYTE") * 8

def u24_be(buf):
    return (buf[0]<<16) | (buf[1]<<8) | buf[2]

with open(img,"rb") as f:
    data = f.read()

def art_read(idx):
    off = art_b + idx*3
    b = data[off:off+3]
    if len(b) != 3:
        raise SystemExit(f"short read ART[{idx}] at byte off={off}")
    return u24_be(b)

v_testg  = art_read(43)  # TESTG
v_base63 = art_read(63)  # TESTSCR_BASE
v_end64  = art_read(64)  # TESTSCR_END

assert v_testg  == testscr_base_bit, (v_testg, testscr_base_bit)
assert v_base63 == testscr_base_bit, (v_base63, testscr_base_bit)
assert v_end64  == testscr_end_bit,  (v_end64, testscr_end_bit)

print("OK scratch artifacts:",
      "TESTG", v_testg,
      "BASE63", v_base63,
      "END64", v_end64)
PY
