#!/bin/sh
set -eu

# usage:
#   scripts/cleanup_backups.sh           # dry-run
#   scripts/cleanup_backups.sh --apply   # move backups into bak/cleanup_TIMESTAMP/

APPLY=0
if [ "${1:-}" = "--apply" ]; then
  APPLY=1
fi

ts="$(date +%Y%m%d_%H%M%S)"
DST="bak/cleanup_${ts}"
mkdir -p "$DST"

# find only backup files of our typical form *.bak.YYYY...
# (не трогаем .7z и вообще ничего кроме *.bak.*)
list="$(find . -type f -name "*.bak.*" | sed 's|^\./||')"

if [ -z "$list" ]; then
  echo "[cleanup] no *.bak.* files found" >&2
  exit 0
fi

echo "[cleanup] target: $DST" >&2
echo "$list" | while IFS= read -r f; do
  echo "[cleanup] $f" >&2
done

if [ "$APPLY" -eq 0 ]; then
  echo "[cleanup] dry-run only. Re-run with --apply to move." >&2
  exit 0
fi

echo "$list" | while IFS= read -r f; do
  d="$(dirname "$f")"
  mkdir -p "$DST/$d"
  mv "$f" "$DST/$f"
done

echo "[cleanup] moved backups into $DST" >&2
