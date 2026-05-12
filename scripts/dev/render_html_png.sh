#!/bin/sh
set -eu

if [ $# -ne 2 ]; then
  echo "usage: $0 in.html out.png" >&2
  exit 2
fi

IN_HTML="$1"
OUT_PNG="$2"

if [ ! -f "$IN_HTML" ]; then
  echo "ERROR: input HTML not found: $IN_HTML" >&2
  exit 1
fi

CHROME="$(command -v google-chrome-stable || true)"
if [ -z "$CHROME" ]; then
  CHROME="$(command -v google-chrome || true)"
fi

if [ -z "$CHROME" ]; then
  echo "ERROR: google-chrome-stable or google-chrome not found" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUT_PNG")" tmp

IN_ABS="$(python3 - <<PY
from pathlib import Path
print(Path("$IN_HTML").resolve())
PY
)"

OUT_ABS="$(python3 - <<PY
from pathlib import Path
print(Path("$OUT_PNG").resolve())
PY
)"

# Chrome writes screenshot into the directory specified by --screenshot=PATH
# It may overwrite without prompting.
"$CHROME" \
  --headless=new \
  --disable-gpu \
  --no-sandbox \
  --window-size=1280,720 \
  --screenshot="$OUT_ABS" \
  "file://$IN_ABS" \
  >/dev/null 2>&1 || true

if [ ! -f "$OUT_ABS" ]; then
  echo "ERROR: screenshot was not created: $OUT_ABS" >&2
  exit 1
fi

echo "wrote: $OUT_ABS"
