#!/bin/sh
set -eu

# file: scripts/metrics_loc.sh
# date: 2026-05-05
# purpose: print project LOC metrics (prefers cloc, falls back to wc -l)

EXCL="build,tmp,out,bak"

if command -v cloc >/dev/null 2>&1; then
  echo "[metrics] using cloc"
  cloc \
    --exclude-dir="$EXCL" \
    --quiet \
    --by-file-by-lang \
    --sum-one \
    src scripts doc
else
  echo "[metrics] cloc not found; fallback to wc -l (raw lines)"
  find src scripts doc \
    \( -path './build' -o -path './tmp' -o -path './out' -o -path './bak' \) -prune -o \
    -type f \( -name '*.c' -o -name '*.h' -o -name '*.sh' -o -name '*.py' -o -name '*.md' \) -print \
    | xargs wc -l
fi
