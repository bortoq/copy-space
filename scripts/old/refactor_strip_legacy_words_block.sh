#!/bin/sh
set -eu

LEG="src/mkimage/std7_fixed/legacy.c"
test -f "$LEG"

ts="$(date +%Y%m%d_%H%M%S)"
cp -a "$LEG" "$LEG.bak.strip.$ts"
echo "[strip] backup $LEG -> $LEG.bak.strip.$ts" >&2

python3 - <<'PY'
from pathlib import Path
import re

p = Path("src/mkimage/std7_fixed/legacy.c")
s = p.read_text(encoding="utf-8", errors="replace")

m0 = re.search(r'^\s*static\s+void\s+nop_fill_image\s*\(', s, flags=re.M)
m1 = re.search(r'^\s*static\s+void\s+usage\s*\(', s, flags=re.M)
if not m0 or not m1 or m1.start() <= m0.start():
    raise SystemExit("cannot find region: need 'static void nop_fill_image(' and later 'static void usage('")

s2 = s[:m0.start()] + "/* extracted to words_all.c */\n\n" + s[m1.start():]

p.write_text(s2, encoding="utf-8")
print("[strip] OK: removed words/functions block from legacy.c")
PY

echo "[strip] sanity checks:" >&2
grep -n "static void nop_fill_processor" -n src/mkimage/std7_fixed/legacy.c || true
grep -n "static void write_cell" -n src/mkimage/std7_fixed/legacy.c || true