#!/bin/sh
set -u

usage() {
  echo "usage:" >&2
  echo "  $0 --csv demands.csv --bw N [--slots N] [--outdir DIR]" >&2
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

mkdir -p "$OUTDIR"

INST="$OUTDIR/instance.json"
SB="$OUTDIR/schedule_baseline.json"
SG="$OUTDIR/schedule_greedy.json"
RB="$OUTDIR/report_baseline.json"
RG="$OUTDIR/report_greedy.json"

# 1) CSV -> instance
if [ -n "$SLOTS" ]; then
  python3 scripts/scheduler/csv_to_instance_v0.py "$CSV" --bw "$BW" --slots "$SLOTS" --out "$INST" || exit 1
else
  python3 scripts/scheduler/csv_to_instance_v0.py "$CSV" --bw "$BW" --out "$INST" || exit 1
fi

# 2) solve + validate baseline
python3 scripts/scheduler/solve_v0.py "$INST" --out "$SB" --solver baseline || exit 1
python3 scripts/scheduler/validate_v0.py "$INST" "$SB" --report "$RB" --quiet >/dev/null 2>/dev/null || exit 1

# 3) solve + validate greedy
python3 scripts/scheduler/solve_v0.py "$INST" --out "$SG" --solver greedy || exit 1
python3 scripts/scheduler/validate_v0.py "$INST" "$SG" --report "$RG" --quiet >/dev/null 2>/dev/null || exit 1

# 4) summary
python3 - "$RB" "$RG" <<'PY'
import json, sys
b = json.load(open(sys.argv[1], "r", encoding="utf-8"))
g = json.load(open(sys.argv[2], "r", encoding="utf-8"))
def line(name, r):
    print(f"{name:8s} status={r.get('status')} ticks={r.get('ticks_total')} util={float(r.get('utilization',0.0)):.4f} bpt={float(r.get('bits_per_tick',0.0)):.2f} lb={r.get('max_degree_chunks',0)}")
line("baseline", b)
line("greedy", g)
if b.get("status")=="PASS" and g.get("status")=="PASS":
    print("delta_ticks_total:", int(b["ticks_total"]) - int(g["ticks_total"]))
PY

echo "[pilot] wrote artifacts to: $OUTDIR" >&2
