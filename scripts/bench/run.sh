#!/bin/sh
set -eu

# file: scripts/bench/run.sh
# purpose: unified benchmark runner -> one CSV file (schema v0), with simple sweeps
#
# Examples:
#   scripts/bench/run.sh --bench all --out tmp/bench.csv
#   scripts/bench/run.sh --bench pack --out tmp/pack.csv --copies-list 64,128 --chunk-bytes-list 32,64
#   scripts/bench/run.sh --bench permute --out tmp/p.csv --mode-list random --seed-list 1,2,3
#
# List syntax: comma-separated and/or space-separated (e.g. "64,128" or "64 128").

usage() {
  echo "usage: $0 --bench {pack|permute|bulkcopy|all} --out file.csv [sweep options...]" >&2
  echo "sweep options:" >&2
  echo "  --copies-list STR" >&2
  echo "  --chunk-bytes-list STR" >&2
  echo "  --src-stride-bytes-list STR   (pack)" >&2
  echo "  --mode-list STR               (permute)" >&2
  echo "  --seed-list STR               (permute; also passed through pack notes)" >&2
  echo "  --len-bytes-list STR          (bulkcopy)" >&2
  echo "  --life-list STR               (bulkcopy)" >&2
  echo "  --repeat N" >&2
  exit 2
}

BENCH=""
OUT=""

# defaults (single values)
COPIES_LIST="${COPIES_LIST:-64}"
CHUNK_BYTES_LIST="${CHUNK_BYTES_LIST:-64}"
SRC_STRIDE_BYTES_LIST="${SRC_STRIDE_BYTES_LIST:-4096}"
MODE_LIST="${MODE_LIST:-random}"
SEED_LIST="${SEED_LIST:-1}"
LEN_BYTES_LIST="${LEN_BYTES_LIST:-65536}"
LIFE_LIST="${LIFE_LIST:-20000}"
REPEAT="${REPEAT:-1}"

while [ $# -gt 0 ]; do
  case "$1" in
    --bench) BENCH="${2:-}"; shift 2;;
    --out) OUT="${2:-}"; shift 2;;

    --copies-list) COPIES_LIST="${2:-}"; shift 2;;
    --chunk-bytes-list) CHUNK_BYTES_LIST="${2:-}"; shift 2;;
    --src-stride-bytes-list) SRC_STRIDE_BYTES_LIST="${2:-}"; shift 2;;
    --mode-list) MODE_LIST="${2:-}"; shift 2;;
    --seed-list) SEED_LIST="${2:-}"; shift 2;;
    --len-bytes-list) LEN_BYTES_LIST="${2:-}"; shift 2;;
    --life-list) LIFE_LIST="${2:-}"; shift 2;;
    --repeat) REPEAT="${2:-}"; shift 2;;

    *) usage;;
  esac
done

[ -n "$BENCH" ] || usage
[ -n "$OUT" ] || usage

# Normalize list: commas -> spaces
norm_list() {
  printf "%s" "$1" | tr ',' ' '
}

need_bin() { [ -x "$1" ] || { echo "ERROR: missing binary: $1 (run: make bins)" >&2; exit 1; }; }

# Ensure tools exist
if [ ! -x build/bin/mkimage_std7_fixed ] || [ ! -x build/bin/vmrun ] || [ ! -x build/bin/forth0c ]; then
  make bins >/dev/null
fi

need_bin build/bin/mkimage_std7_fixed
need_bin build/bin/vmrun
need_bin build/bin/vmprep_forth0
need_bin build/bin/forth0c

mkdir -p "$(dirname "$OUT")" tmp

# Write header (single source of truth)
python3 scripts/vmrep_to_csv.py --header > "$OUT"

run_pack() {
  for COPIES in $(norm_list "$COPIES_LIST"); do
    for CHUNK_BYTES in $(norm_list "$CHUNK_BYTES_LIST"); do
      for SRC_STRIDE_BYTES in $(norm_list "$SRC_STRIDE_BYTES_LIST"); do
        for SEED in $(norm_list "$SEED_LIST"); do
          i=0
          while [ "$i" -lt "$REPEAT" ]; do
            export COPIES CHUNK_BYTES SRC_STRIDE_BYTES SEED
            scripts/bench_pack_csv.sh --row >> "$OUT"
            i=$((i+1))
          done
        done
      done
    done
  done
}

run_permute() {
  for COPIES in $(norm_list "$COPIES_LIST"); do
    for CHUNK_BYTES in $(norm_list "$CHUNK_BYTES_LIST"); do
      for MODE in $(norm_list "$MODE_LIST"); do
        for SEED in $(norm_list "$SEED_LIST"); do
          i=0
          while [ "$i" -lt "$REPEAT" ]; do
            export COPIES CHUNK_BYTES MODE SEED
            scripts/bench_permute_csv.sh --row >> "$OUT"
            i=$((i+1))
          done
        done
      done
    done
  done
}

run_bulkcopy() {
  for LEN_BYTES in $(norm_list "$LEN_BYTES_LIST"); do
    for LIFE in $(norm_list "$LIFE_LIST"); do
      i=0
      while [ "$i" -lt "$REPEAT" ]; do
        export LEN_BYTES LIFE
        scripts/bench_bulkcopy_csv.sh --row >> "$OUT"
        i=$((i+1))
      done
    done
  done
}

case "$BENCH" in
  pack) run_pack;;
  permute) run_permute;;
  bulkcopy) run_bulkcopy;;
  all)
    run_pack
    run_permute
    run_bulkcopy
    ;;
  *) usage;;
esac

echo "[bench] wrote $OUT" >&2
