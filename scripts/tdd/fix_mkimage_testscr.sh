#!/bin/sh
set -eu

F="src/mkimage/mkimage_std7_fixed.c"
test -f "$F"

ts="$(date +%Y%m%d_%H%M%S)"
cp -a "$F" "$F.bak.$ts"
echo "[fix] backup $F -> $F.bak.$ts" >&2

python3 - "$F" <<'PY'
import sys, re
from pathlib import Path

path = Path(sys.argv[1])
s = path.read_text(encoding="utf-8", errors="replace")

# 0) Remove the wrong, currently-in-error-branch prints if present
s = re.sub(r'^\s*printf\("  TESTSCR_BASE\(byte\)=.*\n', '', s, flags=re.M)
s = re.sub(r'^\s*printf\("  TESTSCR_SIZE\(byte\)=.*\n', '', s, flags=re.M)

# 1) Ensure TESTSCR constants exist after WORDS_BASE computation
# Insert after the line: bitaddr_t WORDS_BASE = ...
m = re.search(r'^\s*bitaddr_t\s+WORDS_BASE\s*=\s*.*?;\s*$', s, flags=re.M)
if not m:
    raise SystemExit("cannot find WORDS_BASE assignment line")

if "TESTSCR_SIZE_BYTES" not in s:
    ins = r'''
  /* standardized test scratch region (fixed relative to WORDS_BASE; independent of POOL_CELLS) */
  const size_t TESTSCR_SIZE_BYTES = 8192u;
  const bitaddr_t TESTSCR_SIZE_BITS = (bitaddr_t)TESTSCR_SIZE_BYTES * 8u;
  bitaddr_t TESTSCR_BASE = (WORDS_BASE >= TESTSCR_SIZE_BITS) ? (WORDS_BASE - TESTSCR_SIZE_BITS) : 0;
'''
    s = s[:m.end()] + ins + s[m.end():]

# 2) Strengthen overlap check to ensure pool does not overlap scratch+guard
# Replace: if (pool_end + 4096u > WORDS_BASE) {
# with:    if (pool_end + 4096u + TESTSCR_SIZE_BITS > WORDS_BASE) {
s2, n = re.subn(r'if\s*\(\s*pool_end\s*\+\s*4096u\s*>\s*WORDS_BASE\s*\)\s*\{',
                r'if (pool_end + 4096u + TESTSCR_SIZE_BITS > WORDS_BASE) {',
                s, count=1)
if n != 1:
    # maybe already patched or uses different guard; don't hard-fail, but warn
    s2 = s
s = s2

# 3) Insert printing of TESTSCR in the normal "Built std7_fixed..." summary section.
# Insert right after the big fprintf(stderr, "Built std7_fixed ... OFFTAB...", ... );
if "TESTSCR_BASE(byte)=" not in s:
    # Find the end of the big summary fprintf(...) by locating the first occurrence of 'OFFTAB>>3));'
    anchor = "OFFTAB>>3));"
    idx = s.find(anchor)
    if idx < 0:
        raise SystemExit("cannot find anchor 'OFFTAB>>3));' to insert TESTSCR prints")
    insert_at = idx + len(anchor)
    ins2 = r'''
  fprintf(stderr, "  TESTSCR_BASE(byte)=%llu\n", (unsigned long long)(TESTSCR_BASE>>3));
  fprintf(stderr, "  TESTSCR_SIZE(byte)=%llu\n", (unsigned long long)TESTSCR_SIZE_BYTES);
'''
    s = s[:insert_at] + "\n" + ins2 + s[insert_at:]

path.write_text(s, encoding="utf-8")
print("[fix] mkimage_std7_fixed.c patched: TESTSCR computed+printed in normal path")
PY

echo "[fix] rebuild required: make clean && make" >&2