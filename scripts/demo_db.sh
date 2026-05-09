#!/bin/sh
set -eu

# file: scripts/demo_db.sh
# date: 2026-05-05
# purpose: quick partner-facing DB/analytics demo
#
# stdout: CSV (header + rows)
# stderr: progress
#
# CSV file behavior:
# - if DEMO_CSV is UNSET: default to tmp/demo.csv (always)
# - if DEMO_CSV is set to empty: disable file saving
# - if DEMO_CSV is a path: save there

if [ -n "${DEMO_RUNNING:-}" ]; then
  exit 0
fi
export DEMO_RUNNING=1

mkdir -p tmp
log() { printf "%s\n" "$*" >&2; }

# default DEMO_CSV if it is truly UNSET
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

HEADER="$(python3 scripts/vmrep_to_csv.py --header)"
emit_line "$HEADER"

log "[demo] PACK: ${PACK_COPIES}x${PACK_CHUNK_BYTES}B (stride=${PACK_SRC_STRIDE_BYTES})"
export COPIES="$PACK_COPIES" CHUNK_BYTES="$PACK_CHUNK_BYTES" SRC_STRIDE_BYTES="$PACK_SRC_STRIDE_BYTES"
row="$(scripts/bench_pack_csv.sh --row)"
emit_line "$row"

log "[demo] PERMUTE: ${PERMUTE_COPIES}x${PERMUTE_CHUNK_BYTES}B (mode=${PERMUTE_MODE}, seed=${PERMUTE_SEED})"
export COPIES="$PERMUTE_COPIES" CHUNK_BYTES="$PERMUTE_CHUNK_BYTES" MODE="$PERMUTE_MODE" SEED="$PERMUTE_SEED"
row="$(scripts/bench_permute_csv.sh --row)"
emit_line "$row"

if [ "${DEMO_BULKCOPY:-1}" = "1" ]; then
  log "[demo] BULKCOPY: LEN_BYTES=${BULK_LEN_BYTES} (LIFE=${BULK_LIFE})"
  export LEN_BYTES="$BULK_LEN_BYTES" LIFE="$BULK_LIFE"
  row="$(scripts/bench_bulkcopy_csv.sh --row)"
  emit_line "$row"
fi

if [ "${DEMO_TDD:-0}" = "1" ]; then
  log "[demo] TDD"
  make tdd >/dev/null
  log "[demo] TDD OK"
fi

if [ -n "${DEMO_CSV:-}" ]; then
  log "[demo] wrote CSV: $DEMO_CSV"
fi
