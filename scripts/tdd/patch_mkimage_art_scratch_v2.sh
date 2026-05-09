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

# 0) Remove any stray TESTSCR prints (we will re-add in the correct place)
s = re.sub(r'^\s*(?:printf|fprintf)\([^;]*TESTSCR_BASE\(byte\)[^;]*;\s*\n', '', s, flags=re.M)
s = re.sub(r'^\s*(?:printf|fprintf)\([^;]*TESTSCR_SIZE\(byte\)[^;]*;\s*\n', '', s, flags=re.M)

# 1) Ensure TESTSCR constants exist after WORDS_BASE assignment
m = re.search(r'^\s*bitaddr_t\s+WORDS_BASE\s*=\s*.*?;\s*$', s, flags=re.M)
if not m:
    raise SystemExit("mkimage: cannot find WORDS_BASE assignment line")

if "TESTSCR_SIZE_BYTES" not in s:
    ins = r'''
  /* standardized test scratch region (fixed relative to WORDS_BASE; independent of POOL_CELLS) */
  const size_t TESTSCR_SIZE_BYTES = 8192u;
  const bitaddr_t TESTSCR_SIZE_BITS = (bitaddr_t)TESTSCR_SIZE_BYTES * 8u;
  bitaddr_t TESTSCR_BASE = (WORDS_BASE >= TESTSCR_SIZE_BITS) ? (WORDS_BASE - TESTSCR_SIZE_BITS) : 0;
'''
    s = s[:m.end()] + ins + s[m.end():]

# 2) Strengthen overlap check if present: pool_end + 4096u > WORDS_BASE  => + TESTSCR_SIZE_BITS
s = re.sub(r'if\s*\(\s*pool_end\s*\+\s*4096u\s*>\s*WORDS_BASE\s*\)\s*\{',
           r'if (pool_end + 4096u + TESTSCR_SIZE_BITS > WORDS_BASE) {',
           s, count=1)

# 3) Patch ART[43] write: replace last arg with (uint64_t)TESTSCR_BASE
# We match the whole vm_write_uint(...) statement that contains "ART + 43*"
pat43 = re.compile(r'^\s*vm_write_uint\(\s*&vm\s*,\s*ART\s*\+\s*43\*.*?;\s*$', re.M)
m43 = pat43.search(s)
if not m43:
    # try looser: might be split across multiple lines; match from "vm_write_uint(" to ");" containing "ART + 43*"
    pat43b = re.compile(r'vm_write_uint\(\s*&vm\s*,\s*ART\s*\+\s*43\*[\s\S]*?\);\s*', re.M)
    m43 = pat43b.search(s)
    if not m43:
        raise SystemExit("mkimage: cannot locate vm_write_uint for ART[43]")

stmt = s[m43.start():m43.end()]

# Replace the last argument of vm_write_uint(..., <LAST>);
# We do it by replacing the tail ", <something>);" with ", (uint64_t)TESTSCR_BASE);"
stmt2, n = re.subn(r',\s*\(uint64_t\)\s*[^,\)]*\s*\)\s*\)\s*;',
                   r', (uint64_t)TESTSCR_BASE);',
                   stmt, count=1)
if n != 1:
    # maybe last arg is not written as "(uint64_t)X" but something else; do a more general replacement:
    stmt2, n = re.subn(r',\s*[^,\)]*\)\s*;',
                       r', (uint64_t)TESTSCR_BASE);',
                       stmt, count=1)
    if n != 1:
        raise SystemExit("mkimage: failed to rewrite ART[43] statement last arg")

s = s[:m43.start()] + stmt2 + s[m43.end():]

# 4) Append ART[63], ART[64] after ART[62] write
if "ART +63*" not in s and "ART + 63*" not in s:
    m62 = re.search(r'vm_write_uint\(\s*&vm\s*,\s*ART\s*\+\s*62\*[\s\S]*?\);\s*', s, flags=re.M)
    if not m62:
        raise SystemExit("mkimage: cannot find ART[62] write to append after")
    ins = r'''
  /* standardized test scratch artifacts (appended) */
  vm_write_uint(&vm, ART +63*(bitaddr_t)vm.addr_bits, vm.addr_bits, (uint64_t)TESTSCR_BASE);
  vm_write_uint(&vm, ART +64*(bitaddr_t)vm.addr_bits, vm.addr_bits, (uint64_t)(TESTSCR_BASE + TESTSCR_SIZE_BITS));
'''
    s = s[:m62.end()] + ins + s[m62.end():]

# 5) Ensure summary prints include ART(byte), TESTSCR_BASE/SIZE
if "ART(byte)=" not in s or "TESTSCR_BASE(byte)=" not in s or "TESTSCR_SIZE(byte)=" not in s:
    # find the summary fprintf that contains "Built std7_fixed"
    k = s.find("Built std7_fixed")
    if k < 0:
        raise SystemExit("mkimage: cannot find 'Built std7_fixed' summary fprintf")

    end_call = s.find(");", k)
    if end_call < 0:
        raise SystemExit("mkimage: cannot find end of summary fprintf(...) call")

    add = r'''
  fprintf(stderr, "  ART(byte)=%llu\n", (unsigned long long)(ART>>3));
  fprintf(stderr, "  TESTSCR_BASE(byte)=%llu\n", (unsigned long long)(TESTSCR_BASE>>3));
  fprintf(stderr, "  TESTSCR_SIZE(byte)=%llu\n", (unsigned long long)TESTSCR_SIZE_BYTES);
'''
    s = s[:end_call+2] + add + s[end_call+2:]

path.write_text(s, encoding="utf-8")
print("[patch] mkimage: scratch artifacts + prints installed (v2)")
PY

echo "[patch] rebuild: make clean && make" >&2