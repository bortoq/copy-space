#!/bin/sh
set -eu

usage() {
  echo "usage:" >&2
  echo "  $0 --csv demands.csv --bw N [--slots N] [--outdir DIR]" >&2
  echo >&2
  echo "Note: this is a thin wrapper around the Python pilot runner." >&2
  echo "Preferred: copyspace-pilot (after pip install -e .)" >&2
  exit 2
}

CSV=""
BW=""
SLOTS=""
OUTDIR="tmp/pilot"

while [ $# -gt 0 ]; do
  case "$1" in
    --csv) CSV="${2:-}"; shift 2;;
    --bw) BW="${2:-}"; shift 2;;
    --slots) SLOTS="${2:-}"; shift 2;;
    --outdir) OUTDIR="${2:-}"; shift 2;;
    *) usage;;
  esac
done

[ -n "$CSV" ] || usage
[ -n "$BW" ] || usage
[ -f "$CSV" ] || { echo "ERROR: missing CSV file: $CSV" >&2; exit 1; }

if [ -n "$SLOTS" ]; then
  python3 -m copyspace.v0.pilot --csv "$CSV" --bw "$BW" --slots "$SLOTS" --outdir "$OUTDIR"
else
  python3 -m copyspace.v0.pilot --csv "$CSV" --bw "$BW" --outdir "$OUTDIR"
fi
