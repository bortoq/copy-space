#!/bin/sh
set -eu

mkdir -p tools

# pinned version tag (can be changed)
URL="https://raw.githubusercontent.com/AlDanial/cloc/v2.02/cloc"

OUT="tools/cloc"
if [ -f "$OUT" ]; then
  echo "OK: already exists: $OUT"
  exit 0
fi

if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$URL" -o "$OUT"
elif command -v wget >/dev/null 2>&1; then
  wget -q "$URL" -O "$OUT"
else
  echo "FAIL: need curl or wget to download cloc" >&2
  exit 1
fi

chmod +x "$OUT"
echo "OK: downloaded $OUT"
echo "Run:"
echo "  perl tools/cloc --version"
