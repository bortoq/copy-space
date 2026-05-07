#!/bin/sh
set -eu

# file: scripts/bench/run.sh
# purpose: unified benchmark runner -> one CSV file (schema v0)
#
# Examples:
#   scripts/bench/run.sh --bench all --out tmp/bench.csv
#   scripts/bench/run.sh --bench pack --out tmp/pack.csv
#
# Notes:
# - each bench wrapper prints header+row by default; we use --row and write one header here.
# - supports a minimal parameter sweep via env vars per bench.

usage() {
  echo "usage: $0 --bench {pack|permute|bulkcopy|all} --out file.csv" >&2
  exit 2
}

BENCH=""
OUT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --bench) BENCH="${2:-}"; shift 2;;
    --out) OUT="${2:-}"; shift 2;;
    *) usage;;
  esac
done

[ -n "$BENCH" ] || usage
[ -n "$OUT" ] || usage

need_bin() { [ -x "$1" ] || { echo "ERROR: missing binary: $1 (run: make bins)" >&2; exit 1; }; }

# Ensure tools exist
if [ ! -x build/bin/mkimage_std7_fixed ] || [ ! -x build/bin/vmrun ] || [ ! -x build/bin/forth0c ]; then
  make bins >/dev/null
fi

need_bin build/bin/mkimage_std7_fixed
need_bin build/bin/vmrun
need_bin build/bin/vmprep_forth0
need_bin build/bin/forth0c

mkdir -p "$(dirname "$OUT")" tmp

# Write header
python3 scripts/vmrep_to_csv.py --header > "$OUT"

run_pack() {
  scripts/bench_pack_csv.sh --row >> "$OUT"
}

run_permute() {
  scripts/bench_permute_csv.sh --row >> "$OUT"
}

run_bulkcopy() {
  scripts/bench_bulkcopy_csv.sh --row >> "$OUT"
}

case "$BENCH" in
  pack) run_pack;;
  permute) run_permute;;
  bulkcopy) run_bulkcopy;;
  all)
    run_pack
    run_permute
    run_bulkcopy
    ;;
  *) usage;;
esac

echo "[bench] wrote $OUT" >&2
