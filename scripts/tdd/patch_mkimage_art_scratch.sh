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

# 1) Ensure TESTSCR_BASE exists after WORDS_BASE assignment
m = re.search(r'^\s*bitaddr_t\s+WORDS_BASE\s*=\s*.*?;\s*$', s, flags=re.M)
if not m:
    raise SystemExit("cannot find WORDS_BASE assignment")

if "TESTSCR_SIZE_BYTES" not in s:
    ins = r'''
  /* standardized test scratch region (fixed relative to WORDS_BASE; independent of POOL_CELLS) */
  const size_t TESTSCR_SIZE_BYTES = 8192u;
  const bitaddr_t TESTSCR_SIZE_BITS = (bitaddr_t)TESTSCR_SIZE_BYTES * 8u;
  bitaddr_t TESTSCR_BASE = (WORDS_BASE >= TESTSCR_SIZE_BITS) ? (WORDS_BASE - TESTSCR_SIZE_BITS) : 0;
'''
    s = s[:m.end()] + ins + s[m.end():]

# 2) Make ART[43] (TESTG) point to TESTSCR_BASE
s2, n = re.subn(
    r'(vm_write_uint\(&vm,\s*ART\s*\+\s*43\*\(bitaddr_t\)vm\.addr_bits,\s*vm\.addr_bits,\s*\(uint64_t\)\s*)([A-Za-z0-9_]+)(\s*\)\s*\)\s*;)',
    r'\1TESTSCR_BASE\3',
    s,
    count=1
)
if n != 1:
    raise SystemExit("cannot patch ART[43] write (TESTG)")

s = s2

# 3) Append ART[63] and ART[64] after ART[62] write
if re.search(r'ART\s*\+\s*63\*', s) or re.search(r'ART\s*\+\s*64\*', s):
    pass
else:
    m62 = re.search(r'^\s*vm_write_uint\(&vm,\s*ART\s*\+\s*62\*\(bitaddr_t\)vm\.addr_bits,.*?;\s*$', s, flags=re.M)
    if not m62:
        raise SystemExit("cannot find ART[62] write to append after")
    ins = r'''
  /* standardized test scratch artifacts (appended) */
  vm_write_uint(&vm, ART +63*(bitaddr_t)vm.addr_bits, vm.addr_bits, (uint64_t)TESTSCR_BASE);
  vm_write_uint(&vm, ART +64*(bitaddr_t)vm.addr_bits, vm.addr_bits, (uint64_t)(TESTSCR_BASE + TESTSCR_SIZE_BITS));
'''
    s = s[:m62.end()] + ins + s[m62.end():]

# 4) Ensure mkimage prints ART(byte), TESTSCR_BASE/SIZE in the normal summary path
if "ART(byte)=" not in s:
    # insert ART(byte) print into the big summary fprintf(stderr, "Built std7_fixed ...")
    # simplest: insert after the existing summary fprintf(...) call by locating "Built std7_fixed" literal
    k = s.find("Built std7_fixed")
    if k < 0:
        raise SystemExit("cannot find 'Built std7_fixed' in mkimage to add ART print")
    semi = s.find(");", k)
    if semi < 0:
        raise SystemExit("cannot find end of summary fprintf(...) call")
    add = r'''
  fprintf(stderr, "  ART(byte)=%llu\n", (unsigned long long)(ART>>3));
'''
    s = s[:semi+2] + add + s[semi+2:]

# Ensure TESTSCR prints exist in normal path
if "TESTSCR_BASE(byte)=" not in s or "TESTSCR_SIZE(byte)=" not in s:
    k = s.find("Built std7_fixed")
    if k < 0:
        raise SystemExit("cannot find 'Built std7_fixed' to add TESTSCR prints")
    semi = s.find(");", k)
    if semi < 0:
        raise SystemExit("cannot find end of summary fprintf(...) call")
    add = r'''
  fprintf(stderr, "  TESTSCR_BASE(byte)=%llu\n", (unsigned long long)(TESTSCR_BASE>>3));
  fprintf(stderr, "  TESTSCR_SIZE(byte)=%llu\n", (unsigned long long)TESTSCR_SIZE_BYTES);
'''
    s = s[:semi+2] + add + s[semi+2:]

path.write_text(s, encoding="utf-8")
print("[patch] mkimage: scratch artifacts + prints installed")
PY

echo "[patch] rebuild: make clean && make" >&2