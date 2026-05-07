#!/bin/sh
set -eu

# file: scripts/bench_bulkcopy_csv.sh
# date: 2026-05-05
# purpose: run bulkcopy bench and output CSV (header+row by default)
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

: "${LEN_BYTES:=65536}"
: "${LIFE:=20000}"

export COPYSPACE_REPORT COPYSPACE_REPORT_FROM COPYSPACE_REPORT_LEN
export LEN_BYTES LIFE

if [ ! -x build/bin/mkimage_std7_fixed ] || [ ! -x build/bin/vmrun ]; then
  make bins >/dev/null
fi

CONSOLE_LOG="tmp/demo_bulkcopy.console.log"
mkdir -p tmp
sh scripts/bench_bulkcopy.sh >"$CONSOLE_LOG" 2>&1 || {
  tail -n 200 "$CONSOLE_LOG" >&2 || true
  exit 1
}
if [ "${VERBOSE:-0}" = "1" ]; then
  cat "$CONSOLE_LOG" >&2
fi

BENCH_LOG="${BENCH_LOG:-}"
if [ -n "$BENCH_LOG" ] && [ -f "$BENCH_LOG" ]; then
  :
else
  BENCH_LOG="$(python3 - <<'PY'
import os, glob
cands=[]
for p in glob.glob("tmp/*.log"):
    try:
        b=open(p,"rb").read()
        if b.find(b"VMREP_END") < 0:
            continue
        st=os.stat(p)
        cands.append((st.st_mtime, st.st_size, p))
    except OSError:
        pass
cands.sort(reverse=True)
print(cands[0][2] if cands else "")
PY
)"
fi

if [ -z "$BENCH_LOG" ] || [ ! -f "$BENCH_LOG" ]; then
  echo "FAIL: cannot find bulkcopy log (set BENCH_LOG=... to override)" >&2
  ls -la tmp >&2 || true
  exit 1
fi

COPIES_TOTAL="1"
EXPECTED_BITS_PER_TICK=$((LEN_BYTES * 8))

if [ "$ROW_ONLY" -eq 0 ]; then
  python3 scripts/vmrep_to_csv.py --header
fi

python3 scripts/vmrep_to_csv.py \
  --bench bulkcopy \
  --mode "" \
  --seed "" \
  --log "$BENCH_LOG" \
  --row-only \
  --copies-total "$COPIES_TOTAL" \
  --expected-bits-per-tick "$EXPECTED_BITS_PER_TICK" \
  --notes "LEN_BYTES=${LEN_BYTES} LIFE=${LIFE}"
