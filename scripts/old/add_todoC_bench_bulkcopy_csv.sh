#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_todoC_add_bench_bulkcopy_csv"
mkdir -p "$bakdir"

F="scripts/bench_bulkcopy_csv.sh"
if [ -f "$F" ]; then
  cp -a "$F" "$bakdir/bench_bulkcopy_csv.sh.bak"
fi

cat >"$F" <<'EOF'
#!/bin/sh
set -eu

# file: scripts/bench_bulkcopy_csv.sh
# date: 2026-05-05
# purpose: run bulkcopy bench with vmrep enabled and print one CSV row

: "${COPYSPACE_REPORT:=1}"
: "${COPYSPACE_REPORT_FROM:=1000}"
: "${COPYSPACE_REPORT_LEN:=5000}"

# ensure tools exist
if [ ! -x build/bin/mkimage_std7_fixed ] || [ ! -x build/bin/vmrun ]; then
  make bins
fi

# Run bench (pass-through env: LEN_BYTES, LIFE, FROM, LEN, etc. if supported)
sh scripts/bench_bulkcopy.sh

# Pick newest tmp/*.log that contains VMREP_END
BENCH_LOG="${BENCH_LOG:-}"
if [ -n "$BENCH_LOG" ] && [ -f "$BENCH_LOG" ]; then
  :
else
  BENCH_LOG="$(python3 - <<'PY'
import os, glob
cands=[]
for p in glob.glob("tmp/*.log"):
    try:
        with open(p,"rb") as f:
            b = f.read()
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
  echo "FAIL: cannot find a tmp/*.log containing VMREP_END (set BENCH_LOG=... to override)" >&2
  ls -la tmp >&2 || true
  exit 1
fi

python3 scripts/vmrep_to_csv.py \
  --bench bulkcopy \
  --mode "${MODE:-}" \
  --seed "${SEED:-}" \
  --log "$BENCH_LOG" \
  --notes "LEN_BYTES=${LEN_BYTES:-} LIFE=${LIFE:-} FROM=${FROM:-} LEN=${LEN:-}"
EOF

chmod +x "$F"
echo "OK: wrote $F (backup in $bakdir if existed)" >&2
