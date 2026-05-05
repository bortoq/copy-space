#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_demo_contrast_params"
mkdir -p "$bakdir"

F="scripts/demo_db.sh"
[ -f "$F" ] || { echo "FAIL: missing $F" >&2; exit 1; }
cp -a "$F" "$bakdir/demo_db.sh.bak"

cat >"$F" <<'EOF'
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

# ---- Demo contrast parameters (override-friendly) ----
# PACK/PERMUTE: 64 x 64B => 4096 B/tick
: "${PACK_COPIES:=64}"
: "${PACK_CHUNK_BYTES:=64}"
: "${PACK_SRC_STRIDE_BYTES:=4096}"

: "${PERMUTE_COPIES:=64}"
: "${PERMUTE_CHUNK_BYTES:=64}"
: "${PERMUTE_MODE:=random}"
: "${PERMUTE_SEED:=1}"

# BULKCOPY: 64KB per tick
: "${BULK_LEN_BYTES:=65536}"
: "${BULK_LIFE:=20000}"

export COPYSPACE_REPORT COPYSPACE_REPORT_FROM COPYSPACE_REPORT_LEN
export VERBOSE

# ensure tools exist
printf "%s\n" "[demo] build tools (make bins)" >&2
make bins >/dev/null

# print CSV header once (stdout)
printf "%s\n" "schema_version,bench,mode,seed,space_bytes,processor_n,addr_bits,ticks_total,moved_bits_total,vmrep_bits_sum_total,vmrep_bits_uniq_dst_total,vmrep_avg_bits_sum_per_tick,vmrep_avg_bits_uniq_dst_per_tick,thr_from,thr_len,thr_avg_bits_sum_per_tick,thr_avg_bits_uniq_dst_per_tick,notes"

# --- PACK ---
PACK_BPT=$((PACK_COPIES * PACK_CHUNK_BYTES))
printf "%s\n" "[demo] PACK (compaction-like): ${PACK_COPIES}x${PACK_CHUNK_BYTES}B => ${PACK_BPT} B/tick" >&2

export COPIES="$PACK_COPIES"
export CHUNK_BYTES="$PACK_CHUNK_BYTES"
export SRC_STRIDE_BYTES="$PACK_SRC_STRIDE_BYTES"
scripts/bench_pack_csv.sh

# --- PERMUTE ---
PERM_BPT=$((PERMUTE_COPIES * PERMUTE_CHUNK_BYTES))
printf "%s\n" "[demo] PERMUTE (reorder-like): ${PERMUTE_COPIES}x${PERMUTE_CHUNK_BYTES}B => ${PERM_BPT} B/tick (mode=${PERMUTE_MODE}, seed=${PERMUTE_SEED})" >&2

export COPIES="$PERMUTE_COPIES"
export CHUNK_BYTES="$PERMUTE_CHUNK_BYTES"
export MODE="$PERMUTE_MODE"
export SEED="$PERMUTE_SEED"
scripts/bench_permute_csv.sh

# --- BULKCOPY ---
if [ "${DEMO_BULKCOPY:-1}" = "1" ]; then
  printf "%s\n" "[demo] BULKCOPY (bulk movement): LEN_BYTES=${BULK_LEN_BYTES} (LIFE=${BULK_LIFE})" >&2
  export LEN_BYTES="$BULK_LEN_BYTES"
  export LIFE="$BULK_LIFE"
  scripts/bench_bulkcopy_csv.sh
fi

if [ "${DEMO_TDD:-0}" = "1" ]; then
  printf "%s\n" "[demo] TDD (includes TERM0 descriptor ABI)" >&2
  make tdd >/dev/null
  printf "%s\n" "[demo] TDD OK" >&2
fi
EOF

chmod +x "$F"
echo "OK: patched $F (backup: $bakdir/demo_db.sh.bak)" >&2
echo "Run: scripts/demo_db.sh > tmp/demo.csv" >&2
echo "Verbose: VERBOSE=1 scripts/demo_db.sh > tmp/demo.csv" >&2
