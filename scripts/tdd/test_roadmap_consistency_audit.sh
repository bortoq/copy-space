#!/bin/sh
set -eu

ROADMAP="doc/roadmap.md"

[ -f "$ROADMAP" ] || { echo "FAIL: missing $ROADMAP" >&2; exit 1; }

# Exactly one active debt execution sequence declaration.
active_count=$(rg -n '^Active debt execution sequence: stages 24-29 only\.$' "$ROADMAP" | wc -l | tr -d ' ')
[ "$active_count" = "1" ] || {
  echo "FAIL: expected exactly one active debt sequence declaration" >&2
  exit 1
}

# Stages 34-41 must be marked as legacy derived.
for n in 34 35 36 37 38 39 40 41; do
  rg -q "^## ${n}\\..*\\[LEGACY DERIVED\\]$" "$ROADMAP" || {
    echo "FAIL: stage ${n} header is not marked [LEGACY DERIVED]" >&2
    exit 1
  }
done

echo "OK roadmap consistency audit"
