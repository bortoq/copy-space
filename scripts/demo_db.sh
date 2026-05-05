#!/bin/sh
set -eu

# file: scripts/demo_db.sh
# date: 2026-05-05
# purpose: quick partner-facing DB/analytics demo (quiet by default)
#
# stdout: CSV (header once + rows)
# stderr: short progress + "what to look at" + measured bytes/tick
#
# VERBOSE=1  -> benches print mkimage/hex/vmrep to stderr (as implemented in bench_*_csv.sh)
# DEMO_TDD=1 -> also runs `make tdd` at the end (to stderr)
#
# Output file:
# - if DEMO_CSV is set: append output there (and still print to stdout)
# - else if stdout is a terminal: default DEMO_CSV=tmp/demo.csv
# - else: no implicit file (use shell redirect if needed)

if [ -n "${DEMO_RUNNING:-}" ]; then
  exit 0
fi
export DEMO_RUNNING=1

mkdir -p tmp

log() { printf "%s\n" "$*" >&2; }

emit_line() {
  line="$1"
  if [ -n "${DEMO_CSV:-}" ]; then
    printf "%s\n" "$line" | tee -a "$DEMO_CSV"
  else
    printf "%s\n" "$line"
  fi
}

# choose default DEMO_CSV only for interactive runs
if [ -z "${DEMO_CSV:-}" ] && [ -t 1 ]; then
  DEMO_CSV="tmp/demo.csv"
fi
if [ -n "${DEMO_CSV:-}" ]; then
  : >"$DEMO_CSV"
  log "[demo] CSV will be saved to: $DEMO_CSV"
fi

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

log "[demo] build tools (make bins)"
make bins >/dev/null

# CSV header once
HEADER="schema_version,bench,mode,seed,space_bytes,processor_n,addr_bits,ticks_total,moved_bits_total,vmrep_bits_sum_total,vmrep_bits_uniq_dst_total,vmrep_avg_bits_sum_per_tick,vmrep_avg_bits_uniq_dst_per_tick,thr_from,thr_len,thr_avg_bits_sum_per_tick,thr_avg_bits_uniq_dst_per_tick,notes"
emit_line "$HEADER"

# helper: parse uniq_dst bits/tick from CSV row (col 13)
csv_uniq_bits_per_tick() {
  echo "$1" | awk -F, '{print $13}'
}
bits_to_bytes() {
  python3 - "$1" <<'PY'
import sys
v = float(sys.argv[1])
print(f"{v/8.0:.3f}")
PY
}

log "[demo] What to look at: column vmrep_avg_bits_uniq_dst_per_tick (bits/tick)."

# --- PACK ---
PACK_BPT=$((PACK_COPIES * PACK_CHUNK_BYTES))
log "[demo] PACK (compaction-like): ${PACK_COPIES}x${PACK_CHUNK_BYTES}B => expected ${PACK_BPT} B/tick"
export COPIES="$PACK_COPIES"
export CHUNK_BYTES="$PACK_CHUNK_BYTES"
export SRC_STRIDE_BYTES="$PACK_SRC_STRIDE_BYTES"
row="$(scripts/bench_pack_csv.sh)"
emit_line "$row"
u="$(csv_uniq_bits_per_tick "$row")"
log "[demo] PACK measured uniq_dst: ${u} bits/tick = $(bits_to_bytes "$u") B/tick"

# --- PERMUTE ---
PERM_BPT=$((PERMUTE_COPIES * PERMUTE_CHUNK_BYTES))
log "[demo] PERMUTE (reorder-like): ${PERMUTE_COPIES}x${PERMUTE_CHUNK_BYTES}B => expected ${PERM_BPT} B/tick (mode=${PERMUTE_MODE}, seed=${PERMUTE_SEED})"
export COPIES="$PERMUTE_COPIES"
export CHUNK_BYTES="$PERMUTE_CHUNK_BYTES"
export MODE="$PERMUTE_MODE"
export SEED="$PERMUTE_SEED"
row="$(scripts/bench_permute_csv.sh)"
emit_line "$row"
u="$(csv_uniq_bits_per_tick "$row")"
log "[demo] PERMUTE measured uniq_dst: ${u} bits/tick = $(bits_to_bytes "$u") B/tick"

# --- BULKCOPY ---
if [ "${DEMO_BULKCOPY:-1}" = "1" ]; then
  log "[demo] BULKCOPY (bulk movement): LEN_BYTES=${BULK_LEN_BYTES} (LIFE=${BULK_LIFE}) => expected ${BULK_LEN_BYTES} B/tick"
  export LEN_BYTES="$BULK_LEN_BYTES"
  export LIFE="$BULK_LIFE"
  row="$(scripts/bench_bulkcopy_csv.sh)"
  emit_line "$row"
  u="$(csv_uniq_bits_per_tick "$row")"
  log "[demo] BULKCOPY measured uniq_dst: ${u} bits/tick = $(bits_to_bytes "$u") B/tick"
fi

if [ "${DEMO_TDD:-0}" = "1" ]; then
  log "[demo] TDD (includes TERM0 descriptor ABI)"
  make tdd >/dev/null
  log "[demo] TDD OK"
fi

