#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_patch_demo_db_default_save"
mkdir -p "$bakdir"

F="scripts/demo_db.sh"
[ -f "$F" ] || { echo "FAIL: missing $F" >&2; exit 1; }
cp -a "$F" "$bakdir/demo_db.sh.bak"

cat >"$F" <<'SH'
#!/bin/sh
set -eu

# file: scripts/demo_db.sh
# date: 2026-05-05
# purpose: quick partner-facing DB/analytics demo (quiet by default)
#
# stdout: CSV (header once + rows)
# stderr: short progress + "what to look at" + measured bytes/tick
#
# VERBOSE=1  -> benches print mkimage/hex/vmrep to stderr
# DEMO_TDD=1 -> also runs `make tdd` at the end (to stderr)
#
# CSV file behavior:
# - if DEMO_CSV is UNSET: default to tmp/demo.csv (always)
# - if DEMO_CSV is set to empty: disable file saving
# - if DEMO_CSV is a path: save there
#
# Recommended usage:
#   scripts/demo_db.sh > /dev/null 2> tmp/demo.stderr
#   cat tmp/demo.csv

if [ -n "${DEMO_RUNNING:-}" ]; then
  exit 0
fi
export DEMO_RUNNING=1

mkdir -p tmp
log() { printf "%s\n" "$*" >&2; }

# default save location if DEMO_CSV is truly UNSET
if [ "${DEMO_CSV+x}" != "x" ]; then
  DEMO_CSV="tmp/demo.csv"
fi

emit_line() {
  line="$1"
  if [ -n "${DEMO_CSV:-}" ]; then
    printf "%s\n" "$line" | tee -a "$DEMO_CSV"
  else
    printf "%s\n" "$line"
  fi
}

# truncate CSV file if saving enabled
if [ -n "${DEMO_CSV:-}" ]; then
  : >"$DEMO_CSV"
  log "[demo] CSV will be saved to: $DEMO_CSV"
fi

: "${COPYSPACE_REPORT:=1}"
: "${COPYSPACE_REPORT_FROM:=1000}"
: "${COPYSPACE_REPORT_LEN:=5000}"

: "${PACK_COPIES:=64}"
: "${PACK_CHUNK_BYTES:=64}"
: "${PACK_SRC_STRIDE_BYTES:=4096}"

: "${PERMUTE_COPIES:=64}"
: "${PERMUTE_CHUNK_BYTES:=64}"
: "${PERMUTE_MODE:=random}"
: "${PERMUTE_SEED:=1}"

: "${BULK_LEN_BYTES:=65536}"
: "${BULK_LIFE:=20000}"

export COPYSPACE_REPORT COPYSPACE_REPORT_FROM COPYSPACE_REPORT_LEN
export VERBOSE

log "[demo] build tools (make bins)"
make bins >/dev/null

HEADER="schema_version,bench,mode,seed,space_bytes,processor_n,addr_bits,ticks_total,moved_bits_total,vmrep_bits_sum_total,vmrep_bits_uniq_dst_total,vmrep_avg_bits_sum_per_tick,vmrep_avg_bits_uniq_dst_per_tick,thr_from,thr_len,thr_avg_bits_sum_per_tick,thr_avg_bits_uniq_dst_per_tick,notes"
emit_line "$HEADER"

csv_uniq_bits_per_tick() { echo "$1" | awk -F, '{print $13}'; }
bits_to_bytes() {
  python3 - "$1" <<'PY'
import sys
v = float(sys.argv[1])
print(f"{v/8.0:.3f}")
PY
}

log "[demo] What to look at: column vmrep_avg_bits_uniq_dst_per_tick (bits/tick)."

# PACK
PACK_BPT=$((PACK_COPIES * PACK_CHUNK_BYTES))
log "[demo] PACK: ${PACK_COPIES}x${PACK_CHUNK_BYTES}B => expected ${PACK_BPT} B/tick"
export COPIES="$PACK_COPIES" CHUNK_BYTES="$PACK_CHUNK_BYTES" SRC_STRIDE_BYTES="$PACK_SRC_STRIDE_BYTES"
row="$(scripts/bench_pack_csv.sh)"
emit_line "$row"
u="$(csv_uniq_bits_per_tick "$row")"
log "[demo] PACK measured: ${u} bits/tick = $(bits_to_bytes "$u") B/tick"

# PERMUTE
PERM_BPT=$((PERMUTE_COPIES * PERMUTE_CHUNK_BYTES))
log "[demo] PERMUTE: ${PERMUTE_COPIES}x${PERMUTE_CHUNK_BYTES}B => expected ${PERM_BPT} B/tick (mode=${PERMUTE_MODE}, seed=${PERMUTE_SEED})"
export COPIES="$PERMUTE_COPIES" CHUNK_BYTES="$PERMUTE_CHUNK_BYTES" MODE="$PERMUTE_MODE" SEED="$PERMUTE_SEED"
row="$(scripts/bench_permute_csv.sh)"
emit_line "$row"
u="$(csv_uniq_bits_per_tick "$row")"
log "[demo] PERMUTE measured: ${u} bits/tick = $(bits_to_bytes "$u") B/tick"

# BULKCOPY
if [ "${DEMO_BULKCOPY:-1}" = "1" ]; then
  log "[demo] BULKCOPY: LEN_BYTES=${BULK_LEN_BYTES} (LIFE=${BULK_LIFE}) => expected ${BULK_LEN_BYTES} B/tick"
  export LEN_BYTES="$BULK_LEN_BYTES" LIFE="$BULK_LIFE"
  row="$(scripts/bench_bulkcopy_csv.sh)"
  emit_line "$row"
  u="$(csv_uniq_bits_per_tick "$row")"
  log "[demo] BULKCOPY measured: ${u} bits/tick = $(bits_to_bytes "$u") B/tick"
fi

if [ "${DEMO_TDD:-0}" = "1" ]; then
  log "[demo] TDD (includes TERM0 descriptor ABI)"
  make tdd >/dev/null
  log "[demo] TDD OK"
fi

if [ -n "${DEMO_CSV:-}" ]; then
  log "[demo] wrote CSV: $DEMO_CSV"
fi
SH

chmod +x "$F"
echo "OK: patched $F (backup: $bakdir/demo_db.sh.bak)" >&2
