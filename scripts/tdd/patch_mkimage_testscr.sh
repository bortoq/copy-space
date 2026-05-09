#!/bin/sh
set -eu

F="src/mkimage/mkimage_std7_fixed.c"
test -f "$F"

ts="$(date +%Y%m%d_%H%M%S)"
cp -a "$F" "$F.bak.$ts"
echo "[patch] backup $F -> $F.bak.$ts" >&2

python3 - "$F" <<'PY'
import sys, re
from pathlib import Path

path = Path(sys.argv[1])
s = path.read_text(encoding="utf-8", errors="replace")

if "TESTSCR_BASE(byte)=" in s and "TESTSCR_SIZE(byte)=" in s:
    print("[patch] mkimage: TESTSCR already present in source (skip)")
    sys.exit(0)

# Find a printf/fprintf that contains "WORDS_BASE(byte)=" and capture the first argument expression.
# Works for both:
#   printf("  WORDS_BASE(byte)=... ", <expr>, ...)
#   fprintf(stderr, "  WORDS_BASE(byte)=... ", <expr>, ...)
pat = re.compile(
    r'(?:printf|fprintf)\s*\(\s*(?:stderr\s*,\s*)?"[^"]*WORDS_BASE\(byte\)=[^"]*"\s*,\s*([^,\)]+)',
    re.S
)
m = pat.search(s)
if not m:
    raise SystemExit("mkimage patch: cannot find printf/fprintf with WORDS_BASE(byte)=... in source")

words_base_expr = m.group(1).strip()

# Insert right after the end of that call statement (after the next ';' following match start)
semi = s.find(";", m.start())
if semi < 0:
    raise SystemExit("mkimage patch: cannot find ';' after WORDS_BASE print call")

ins = f'''
  /* standardized test scratch region (bytes), fixed relative to WORDS_BASE */
  {{
    size_t testscr_size = 8192u;
    size_t testscr_base = ((size_t)({words_base_expr}) >= testscr_size) ? ((size_t)({words_base_expr}) - testscr_size) : 0u;
    fprintf(stderr, "  TESTSCR_BASE(byte)=%zu\\n", testscr_base);
    fprintf(stderr, "  TESTSCR_SIZE(byte)=%zu\\n", testscr_size);
  }}
'''
s = s[:semi+1] + ins + s[semi+1:]

path.write_text(s, encoding="utf-8")
print(f"[patch] mkimage: inserted TESTSCR prints using WORDS_BASE expr: {words_base_expr!r}")
PY

echo "[patch] done. Rebuild required: make clean && make" >&2