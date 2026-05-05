#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_demo_quiet_verbose"
mkdir -p "$bakdir"

backup() {
  f="$1"
  if [ -f "$f" ]; then
    cp -a "$f" "$bakdir/$(echo "$f" | tr '/ ' '__').bak"
  fi
}

[ -d scripts ] || { echo "FAIL: run from project root" >&2; exit 1; }

backup scripts/demo_db.sh
backup scripts/bench_pack_csv.sh
backup scripts/bench_permute_csv.sh
backup scripts/bench_bulkcopy_csv.sh

# ---------------- demo_db.sh ----------------
cat > scripts/demo_db.sh <<'EOF'
#!/bin/sh
set -eu

# file: scripts/demo_db.sh
# date: 2026-05-05
# purpose: quick partner-facing DB/analytics demo (quiet by default)
#
# stdout: CSV (header once + rows)
# stderr: short progress messages
#
# VERBOSE=1  -> prints mkimage/hex/vmrep console output from benches (to stderr)
# DEMO_TDD=1 -> also runs `make tdd` at the end (to stderr)

# recursion/duplicate guard
if [ -n "${DEMO_RUNNING:-}" ]; then
  exit 0
fi
export DEMO_RUNNING=1

# vmrep defaults
: "${COPYSPACE_REPORT:=1}"
: "${COPYSPACE_REPORT_FROM:=1000}"
: "${COPYSPACE_REPORT_LEN:=5000}"

# default demo params (exported so child scripts see them)
: "${COPIES:=64}"
: "${CHUNK_BYTES:=64}"
: "${SRC_STRIDE_BYTES:=4096}"
: "${MODE:=random}"
: "${SEED:=1}"
: "${LEN_BYTES:=65536}"
: "${LIFE:=20000}"

export COPYSPACE_REPORT COPYSPACE_REPORT_FROM COPYSPACE_REPORT_LEN
export COPIES CHUNK_BYTES SRC_STRIDE_BYTES MODE SEED LEN_BYTES LIFE
export VERBOSE

# ensure tools exist
printf "%s\n" "[demo] build tools (make bins)" >&2
make bins >/dev/null

# print CSV header once (stdout)
printf "%s\n" "schema_version,bench,mode,seed,space_bytes,processor_n,addr_bits,ticks_total,moved_bits_total,vmrep_bits_sum_total,vmrep_bits_uniq_dst_total,vmrep_avg_bits_sum_per_tick,vmrep_avg_bits_uniq_dst_per_tick,thr_from,thr_len,thr_avg_bits_sum_per_tick,thr_avg_bits_uniq_dst_per_tick,notes"

printf "%s\n" "[demo] PACK (compaction-like)" >&2
scripts/bench_pack_csv.sh

printf "%s\n" "[demo] PERMUTE (reorder-like)" >&2
scripts/bench_permute_csv.sh

if [ "${DEMO_BULKCOPY:-1}" = "1" ]; then
  printf "%s\n" "[demo] BULKCOPY (bulk movement)" >&2
  scripts/bench_bulkcopy_csv.sh
fi

if [ "${DEMO_TDD:-0}" = "1" ]; then
  printf "%s\n" "[demo] TDD (includes TERM0 descriptor ABI)" >&2
  make tdd >/dev/null
  printf "%s\n" "[demo] TDD OK" >&2
fi
EOF
chmod +x scripts/demo_db.sh

# ---------------- bench_pack_csv.sh ----------------
cat > scripts/bench_pack_csv.sh <<'EOF'
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
EOF
chmod +x scripts/bench_pack_csv.sh

# ---------------- bench_permute_csv.sh ----------------
cat > scripts/bench_permute_csv.sh <<'EOF'
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
EOF
chmod +x scripts/bench_permute_csv.sh

# ---------------- bench_bulkcopy_csv.sh ----------------
cat > scripts/bench_bulkcopy_csv.sh <<'EOF'
#!/bin/sh
set -eu

# file: scripts/bench_bulkcopy_csv.sh
# date: 2026-05-05
# purpose: run bulkcopy bench and output ONE CSV ROW (no header)
#
# VERBOSE=1 -> show bench console output on stderr

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

# bulkcopy bench logs vary; pick newest tmp/*.log containing VMREP_END
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

python3 scripts/vmrep_to_csv.py \
  --bench bulkcopy \
  --mode "" \
  --seed "" \
  --log "$BENCH_LOG" \
  --row-only \
  --notes "LEN_BYTES=${LEN_BYTES} LIFE=${LIFE}"
EOF
chmod +x scripts/bench_bulkcopy_csv.sh

echo "OK: applied quiet demo + verbose mode (backups in $bakdir)" >&2
echo "Run quiet demo:    scripts/demo_db.sh" >&2
echo "Run verbose demo:  VERBOSE=1 scripts/demo_db.sh" >&2
echo "Run with TDD:      DEMO_TDD=1 scripts/demo_db.sh" >&2
