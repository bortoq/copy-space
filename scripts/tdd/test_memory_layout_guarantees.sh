#!/bin/sh
set -eu

need_bin() { test -x "$1" || { echo "ERROR: missing binary: $1 (run: make bins)" >&2; exit 1; }; }

need_bin build/bin/mkimage_std7_fixed

mkdir -p tmp

img="tmp/tdd_memlayout_std7.bin"
log="tmp/tdd_memlayout_mkimage.stderr"

build/bin/mkimage_std7_fixed --out "$img" >/dev/null 2>"$log"

art_byte="$(
  sed -n 's/^[[:space:]]*ART(byte)=\([0-9][0-9]*\).*/\1/p' "$log" | head -n 1 | tr -d '\r'
)"

if [ -z "$art_byte" ]; then
  echo "ERROR: cannot parse ART(byte)=... from mkimage stderr ($log)" >&2
  echo "---- mkimage stderr (head) ----" >&2
  sed -n '1,120p' "$log" >&2
  exit 1
fi

python3 - "$img" "$art_byte" <<'PY'
import sys

path = sys.argv[1]
art_byte = int(sys.argv[2])

ADDR_BYTES = 3  # std7_fixed baseline uses addr_bits=24 (3 bytes per ART entry)

def need(cond, msg):
    if not cond:
        raise SystemExit("ERROR: " + msg)

data = open(path, "rb").read()

def rd_art_u(idx: int) -> int:
    off = art_byte + idx * ADDR_BYTES
    need(off + ADDR_BYTES <= len(data), f"ART[{idx}] out of range (off={off}, len={len(data)})")
    return int.from_bytes(data[off:off+ADDR_BYTES], "big")

TESTG = rd_art_u(43)
BASE  = rd_art_u(63)
END   = rd_art_u(64)
BUS   = rd_art_u(65)
TERM  = rd_art_u(66)

need(TESTG == BASE, f"TESTG != TESTSCR_BASE (TESTG={TESTG}, BASE={BASE})")
need(END > BASE, f"TESTSCR_END <= TESTSCR_BASE (BASE={BASE}, END={END})")

need(BASE % 8 == 0 and END % 8 == 0, f"scratch not byte-aligned (BASE%8={BASE%8}, END%8={END%8})")
need(BASE % 64 == 0 and END % 64 == 0, f"scratch not 64-bit aligned (BASE%64={BASE%64}, END%64={END%64})")

size_bits = END - BASE
need(size_bits % 8 == 0, "scratch size is not a whole number of bytes")
size_bytes = size_bits // 8

need(size_bytes >= 8192, f"scratch too small: {size_bytes} bytes (< 8192)")

need(BUS != 0, "BUS_BASE is 0")
need(TERM != 0, "TERM0_DESC is 0")

print(f"OK: TESTSCR size={size_bytes} bytes; TESTG(byte)={TESTG//8}")
PY
