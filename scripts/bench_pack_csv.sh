#!/bin/sh
set -eu

# file: scripts/bench_pack_csv.sh
# date: 2026-05-05
# purpose: run pack bench and output CSV (header+row by default)
#
#   --row  : print row only
# VERBOSE=1 -> show bench console output on stderr

ROW_ONLY=0
if [ "${1:-}" = "--row" ]; then
  ROW_ONLY=1
  shift
fi

: "${COPYSPACE_REPORT:=1}"
: "${COPYSPACE_REPORT_FROM:=1000}"
: "${COPYSPACE_REPORT_LEN:=5000}"

: "${COPIES:=64}"
: "${CHUNK_BYTES:=64}"
: "${SRC_STRIDE_BYTES:=4096}"

export COPYSPACE_REPORT COPYSPACE_REPORT_FROM COPYSPACE_REPORT_LEN
export COPIES CHUNK_BYTES SRC_STRIDE_BYTES

if [ ! -x build/bin/mkimage_std7_fixed ] || [ ! -x build/bin/vmrun ]; then
  make bins >/dev/null
fi

CONSOLE_LOG="tmp/demo_pack.console.log"
mkdir -p tmp
sh scripts/bench_pack.sh >"$CONSOLE_LOG" 2>&1 || {
  tail -n 200 "$CONSOLE_LOG" >&2 || true
  exit 1
}
if [ "${VERBOSE:-0}" = "1" ]; then
  cat "$CONSOLE_LOG" >&2
fi

BENCH_LOG="${BENCH_LOG:-tmp/bench_pack.log}"
if [ ! -f "$BENCH_LOG" ]; then
  if [ -f tmp/bench_pack.log ]; then BENCH_LOG=tmp/bench_pack.log
  elif [ -f tmp/mkbench_pack.log ]; then BENCH_LOG=tmp/mkbench_pack.log
  else
    echo "FAIL: cannot find pack log (tmp/bench_pack.log or tmp/mkbench_pack.log)" >&2
    ls -la tmp >&2 || true
    exit 1
  fi
fi

# derived metrics
COPIES_TOTAL="$COPIES"
EXPECTED_BITS_PER_TICK=$((COPIES * CHUNK_BYTES * 8))

if [ "$ROW_ONLY" -eq 0 ]; then
  python3 scripts/vmrep_to_csv.py --header
fi

python3 scripts/vmrep_to_csv.py \
  --bench pack \
  --mode "pack" \
  --seed "${SEED:-}" \
  --log "$BENCH_LOG" \
  --row-only \
  --copies-total "$COPIES_TOTAL" \
  --expected-bits-per-tick "$EXPECTED_BITS_PER_TICK" \
  --notes "COPIES=${COPIES} CHUNK_BYTES=${CHUNK_BYTES} SRC_STRIDE_BYTES=${SRC_STRIDE_BYTES}"
