#!/bin/sh
set -eu

LOCK="doc/roadmap_stage_headers.lock"
ROADMAP="doc/roadmap.md"
TMP="tmp/roadmap_stage_headers.current"

[ -f "$LOCK" ] || { echo "FAIL: missing $LOCK" >&2; exit 1; }
[ -f "$ROADMAP" ] || { echo "FAIL: missing $ROADMAP" >&2; exit 1; }

rg '^## [0-9]+\.' "$ROADMAP" > "$TMP"
cmp -s "$LOCK" "$TMP" || {
  echo "FAIL: roadmap structure changed (headers mismatch lock)" >&2
  exit 1
}

echo "OK stage23 minimal freeze scope"
