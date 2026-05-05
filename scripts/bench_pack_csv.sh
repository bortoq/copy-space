#!/bin/sh
set -eu

# file: scripts/bench_pack_csv.sh
# date: 2026-05-05
# purpose: run pack bench and output ONE CSV ROW (no header)
#
# VERBOSE=1 -> show bench console output on stderr

: "${COPYSPACE_REPORT:=1}"
: "${COPYSPACE_REPORT_FROM:=1000}"
: "${COPYSPACE_REPORT_LEN:=5000}"

# defaults (also used in notes)
: "${COPIES:=64}"
: "${CHUNK_BYTES:=64}"
: "${SRC_STRIDE_BYTES:=4096}"

export COPYSPACE_REPORT COPYSPACE_REPORT_FROM COPYSPACE_REPORT_LEN
export COPIES CHUNK_BYTES SRC_STRIDE_BYTES

# ensure tools exist
if [ ! -x build/bin/mkimage_std7_fixed ] || [ ! -x build/bin/vmrun ]; then
  make bins >/dev/null
fi

# run bench, capture console output (mkimage/hex/vmrep), keep it only if VERBOSE=1
CONSOLE_LOG="tmp/demo_pack.console.log"
mkdir -p tmp
sh scripts/bench_pack.sh >"$CONSOLE_LOG" 2>&1 || {
  tail -n 200 "$CONSOLE_LOG" >&2 || true
  exit 1
}
if [ "${VERBOSE:-0}" = "1" ]; then
  cat "$CONSOLE_LOG" >&2
fi

# bench_pack.sh writes vmrep to tmp/bench_pack.log (preferred) or tmp/mkbench_pack.log
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

python3 scripts/vmrep_to_csv.py \
  --bench pack \
  --mode "pack" \
  --seed "${SEED:-}" \
  --log "$BENCH_LOG" \
  --row-only \
  --notes "COPIES=${COPIES} CHUNK_BYTES=${CHUNK_BYTES} SRC_STRIDE_BYTES=${SRC_STRIDE_BYTES}"
