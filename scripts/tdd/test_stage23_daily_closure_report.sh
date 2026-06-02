#!/bin/sh
set -eu

REP="doc/stage23_daily_report.md"
[ -f "$REP" ] || { echo "FAIL: missing $REP" >&2; exit 1; }

# Exactly one blocker and one next gate line.
B=$(rg -n '^- blocker:' "$REP" | wc -l | tr -d ' ')
N=$(rg -n '^- next_gate:' "$REP" | wc -l | tr -d ' ')
[ "$B" = "1" ] || { echo "FAIL: report must contain exactly one blocker" >&2; exit 1; }
[ "$N" = "1" ] || { echo "FAIL: report must contain exactly one next_gate" >&2; exit 1; }

echo "OK stage23 daily closure report"
