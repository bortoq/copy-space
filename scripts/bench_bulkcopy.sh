#!/bin/sh
set -eu

SPACE_BYTES="${SPACE_BYTES:-524288}"
PROCESSOR_N="${PROCESSOR_N:-64}"
LIFE="${LIFE:-20000}"

FROM="${FROM:-1000}"
LEN="${LEN:-5000}"

LEN_BYTES="${LEN_BYTES:-65536}"
PAD_BYTES="${PAD_BYTES:-4096}"

BIN_DIR="build/bin"
OUT_DIR="out"
TMP_DIR="tmp"

VMRUN="$BIN_DIR/vmrun"
MKIMAGE="$BIN_DIR/mkimage_std7_fixed"

BASE_IMG="$OUT_DIR/img_fixed_pool_big.bin"
BENCH_IMG="$TMP_DIR/bench_bulkcopy.bin"
LOG="$TMP_DIR/bench_bulkcopy.log"
MKBENCH_LOG="$TMP_DIR/mkbench_bulkcopy.log"

mkdir -p "$OUT_DIR" "$TMP_DIR"

if [ ! -f "$BASE_IMG" ]; then
  echo "[bench] building base image: $BASE_IMG" >&2
  "$MKIMAGE" --out "$BASE_IMG" --pool-cells 32768 > /dev/null
fi

echo "[bench] build bench image (python)" >&2
if ! python3 scripts/mkbench_bulkcopy.py --image "$BASE_IMG" --out "$BENCH_IMG" \
  --space-bytes "$SPACE_BYTES" --processor-n "$PROCESSOR_N" \
  --len-bytes "$LEN_BYTES" --pad-bytes "$PAD_BYTES" \
  2> "$MKBENCH_LOG"
then
  echo "ERROR: mkbench_bulkcopy failed (see $MKBENCH_LOG)" >&2
  tail -n 120 "$MKBENCH_LOG" >&2 || true
  exit 1
fi

echo "[bench] slot0 hexdump:" >&2
xxd -g 1 -l 16 "$BENCH_IMG" >&2 | head -1 >&2

echo "[bench] run vmrun (no HALT expected), collect vmrep" >&2
rm -f "$LOG" "$TMP_DIR/after.bin"

rc=0
COPYSPACE_REPORT=1 \
COPYSPACE_REPORT_FROM="$FROM" COPYSPACE_REPORT_LEN="$LEN" \
"$VMRUN" --image "$BENCH_IMG" \
  --space-bytes "$SPACE_BYTES" --processor-n "$PROCESSOR_N" \
  --life "$LIFE" --dump "$TMP_DIR/after.bin" \
  < /dev/null > /dev/null 2> "$LOG" || rc=$?

if [ "$rc" -ne 0 ]; then
  echo "WARN: vmrun exited rc=$rc (log: $LOG)" >&2
fi

if grep -q "^\[vmrep\]" "$LOG"; then
  sed -n '/^\[vmrep\]/,/VMREP_END/p' "$LOG" >&2
else
  echo "ERROR: no [vmrep] in $LOG" >&2
  tail -n 200 "$LOG" >&2 || true
  exit 1
fi
