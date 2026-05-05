#!/bin/sh
set -eu

# file: scripts/bench_permute_csv.sh
# date: 2026-05-05
# purpose: run permute bench and output ONE CSV ROW (no header)
#
# VERBOSE=1 -> show bench console output on stderr

: "${COPYSPACE_REPORT:=1}"
: "${COPYSPACE_REPORT_FROM:=1000}"
: "${COPYSPACE_REPORT_LEN:=5000}"

: "${COPIES:=64}"
: "${CHUNK_BYTES:=64}"
: "${MODE:=random}"
: "${SEED:=1}"

export COPYSPACE_REPORT COPYSPACE_REPORT_FROM COPYSPACE_REPORT_LEN
export COPIES CHUNK_BYTES MODE SEED

if [ ! -x build/bin/mkimage_std7_fixed ] || [ ! -x build/bin/vmrun ]; then
  make bins >/dev/null
fi

CONSOLE_LOG="tmp/demo_permute.console.log"
mkdir -p tmp
sh scripts/bench_permute.sh >"$CONSOLE_LOG" 2>&1 || {
  tail -n 200 "$CONSOLE_LOG" >&2 || true
  exit 1
}
if [ "${VERBOSE:-0}" = "1" ]; then
  cat "$CONSOLE_LOG" >&2
fi

# prefer bench-specific logs, fallback to newest tmp/*.log containing VMREP_END
BENCH_LOG="${BENCH_LOG:-tmp/bench_permute.log}"
if [ ! -f "$BENCH_LOG" ]; then
  if [ -f tmp/bench_permute.log ]; then BENCH_LOG=tmp/bench_permute.log
  elif [ -f tmp/mkbench_permute.log ]; then BENCH_LOG=tmp/mkbench_permute.log
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
fi

if [ -z "$BENCH_LOG" ] || [ ! -f "$BENCH_LOG" ]; then
  echo "FAIL: cannot find permute log (set BENCH_LOG=... to override)" >&2
  ls -la tmp >&2 || true
  exit 1
fi

python3 scripts/vmrep_to_csv.py \
  --bench permute \
  --mode "${MODE}" \
  --seed "${SEED}" \
  --log "$BENCH_LOG" \
  --row-only \
  --notes "COPIES=${COPIES} CHUNK_BYTES=${CHUNK_BYTES} MODE=${MODE} SEED=${SEED}"
