#!/bin/sh
set -eu

SPACE_BYTES="${SPACE_BYTES:-524288}"
PROCESSOR_N="${PROCESSOR_N:-64}"
LIFE="${LIFE:-20000}"

FROM="${FROM:-1000}"
LEN="${LEN:-5000}"

COPIES="${COPIES:-32}"
CHUNK_BYTES="${CHUNK_BYTES:-2048}"
SRC_STRIDE_BYTES="${SRC_STRIDE_BYTES:-8192}"
PAD_BYTES="${PAD_BYTES:-4096}"
SEED="${SEED:-1}"
RANDOMIZE="${RANDOMIZE:-0}"   # 1 => random mapping dst_i <- src_perm[i]

BIN_DIR="build/bin"
OUT_DIR="out"
TMP_DIR="tmp"

VMRUN="$BIN_DIR/vmrun"
MKIMAGE="$BIN_DIR/mkimage_std7_fixed"

BASE_IMG="$OUT_DIR/img_fixed_pool_big.bin"
BENCH_IMG="$TMP_DIR/bench_pack.bin"
LOG="$TMP_DIR/bench_pack.log"

mkdir -p "$OUT_DIR" "$TMP_DIR"

if [ ! -f "$BASE_IMG" ]; then
  echo "[bench] building base image: $BASE_IMG" >&2
  "$MKIMAGE" --out "$BASE_IMG" --pool-cells 32768 > /dev/null
fi

echo "[bench] build PACK image" >&2
args=""
if [ "$RANDOMIZE" = "1" ]; then args="--src-randomize --seed $SEED"; fi

# shellcheck disable=SC2086
python3 scripts/mkbench_pack.py --image "$BASE_IMG" --out "$BENCH_IMG" \
  --space-bytes "$SPACE_BYTES" --processor-n "$PROCESSOR_N" \
  --copies "$COPIES" --chunk-bytes "$CHUNK_BYTES" --src-stride-bytes "$SRC_STRIDE_BYTES" \
  --pad-bytes "$PAD_BYTES" \
  $args \
  2> "$TMP_DIR/mkbench_pack.log"

echo "[bench] slot0 hexdump:" >&2
xxd -g 1 -l 16 "$BENCH_IMG" >&2 | head -1 >&2

echo "[bench] run vmrun, collect vmrep" >&2
rm -f "$LOG" "$TMP_DIR/after.bin"

COPYSPACE_REPORT=1 COPYSPACE_REPORT_FROM="$FROM" COPYSPACE_REPORT_LEN="$LEN" \
"$VMRUN" --image "$BENCH_IMG" \
  --space-bytes "$SPACE_BYTES" --processor-n "$PROCESSOR_N" \
  --life "$LIFE" --dump "$TMP_DIR/after.bin" \
  < /dev/null > /dev/null 2> "$LOG" || true

sed -n '/^\[vmrep\]/,/VMREP_END/p' "$LOG" >&2