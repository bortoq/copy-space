#!/bin/sh
set -eu

DATE="2026-05-04"
ts="$(date +%Y%m%d_%H%M%S)"

backup() {
  f="$1"
  test -f "$f"
  cp -a "$f" "$f.bak.$ts"
  echo "[regen] backup $f -> $f.bak.$ts" >&2
}

mkdir -p src/vm/diag src/mkimage/std7_fixed

# ------------------------------------------------------------
# 1) Extract VMREP from src/vm/space.c into src/vm/diag/vmrep.c/h
# ------------------------------------------------------------
SPACE_C="src/vm/space.c"
VMREP_H="src/vm/diag/vmrep.h"
VMREP_C="src/vm/diag/vmrep.c"

if [ -f "$SPACE_C" ] && grep -q "VMREP_BEGIN" "$SPACE_C" && [ ! -f "$VMREP_C" ]; then
  echo "[regen] extracting vmrep from $SPACE_C -> $VMREP_C/$VMREP_H" >&2
  backup "$SPACE_C"

  python3 - <<'PY'
from pathlib import Path
import re

space = Path("src/vm/space.c").read_text(encoding="utf-8", errors="replace")

# extract block between VMREP_BEGIN and VMREP_END comments (inclusive)
m = re.search(r"/\* ===================== VM REPORT.*?/\* ===================================================================== \*/\n", space, flags=re.S)
if not m:
    raise SystemExit("cannot find VMREP block in space.c")

block = space[m.start():m.end()]

# create header
Path("src/vm/diag/vmrep.h").write_text(f"""\
/* file: src/vm/diag/vmrep.h
 * date: 2026-05-04
 * purpose: vmrep (bits-per-tick reporting, latency/throughput window)
 */
#ifndef COPYSPACE_VMREP_H_
#define COPYSPACE_VMREP_H_

#include <stdint.h>
#include <stddef.h>

void vmrep_tick_begin(size_t slots_cap);
void vmrep_note_copy(uint64_t dst, uint64_t n);
void vmrep_tick_end(void);

#endif
""", encoding="utf-8")

# build vmrep.c by converting the extracted block into a compilation unit.
# We keep almost all code, but:
# - remove the big comment banner
# - ensure vmrep_tick_* are non-static functions
# - keep internal helpers static
#
# simplest transformation: take the block, strip the banner comment and "static inline" on exported fns.

b = block
# remove leading banner comment lines down to the first #include <inttypes.h>
k = b.find("#include <inttypes.h>")
if k < 0:
    raise SystemExit("VMREP block missing <inttypes.h>")
b = b[k:]  # start from include

# exported funcs: replace "static inline void vmrep_tick_begin" -> "void ..."
b = b.replace("static inline void vmrep_tick_begin", "void vmrep_tick_begin")
b = b.replace("static inline void vmrep_note_copy", "void vmrep_note_copy")
b = b.replace("static inline void vmrep_tick_end", "void vmrep_tick_end")

# remove VMREP_BEGIN/VMREP_END markers if present
b = re.sub(r"/\* VMREP_BEGIN.*?\*/\n", "", b, flags=re.S)
b = re.sub(r"/\* VMREP_END \*/\n", "", b)

Path("src/vm/diag/vmrep.c").write_text(f"""\
/* file: src/vm/diag/vmrep.c
 * date: 2026-05-04
 * purpose: vmrep implementation (was embedded in space.c)
 */
#include "vmrep.h"
#include <stdlib.h>
#include <string.h>
{b}
""", encoding="utf-8")

# patch space.c: remove the VMREP block and include vmrep.h
space2 = space[:m.start()] + "/* vmrep moved to src/vm/diag/vmrep.c */\n" + space[m.end():]

# insert include after #include "space.h"
space2 = space2.replace('#include "space.h"\n', '#include "space.h"\n#include "diag/vmrep.h"\n', 1)

Path("src/vm/space.c").write_text(space2, encoding="utf-8")
print("OK: vmrep extracted and space.c patched")
PY
else
  echo "[regen] vmrep extraction skipped (either no VMREP block, or vmrep.c already exists)" >&2
fi

# ------------------------------------------------------------
# 2) Move mkimage_std7_fixed.c into src/mkimage/std7_fixed/legacy.c + wrapper main
# ------------------------------------------------------------
MKIMAGE_OLD="src/mkimage/mkimage_std7_fixed.c"
LEGACY="src/mkimage/std7_fixed/legacy.c"
WRAP="src/mkimage/mkimage_std7_fixed.c"

if [ -f "$MKIMAGE_OLD" ] && [ ! -f "$LEGACY" ]; then
  echo "[regen] moving $MKIMAGE_OLD -> $LEGACY and creating wrapper $WRAP" >&2
  backup "$MKIMAGE_OLD"

  # move file
  mkdir -p src/mkimage/std7_fixed
  mv "$MKIMAGE_OLD" "$LEGACY"

  # rename main() -> std7_fixed_legacy_main()
  python3 - <<'PY'
from pathlib import Path
import re

p = Path("src/mkimage/std7_fixed/legacy.c")
s = p.read_text(encoding="utf-8", errors="replace")

# Add file header
if not s.lstrip().startswith("/* file:"):
    s = "/* file: src/mkimage/std7_fixed/legacy.c\n * date: 2026-05-04\n * purpose: legacy monolithic mkimage for std7_fixed (to be split)\n */\n\n" + s

# rename main
s2, n = re.subn(r'\bint\s+main\s*\(', 'int std7_fixed_legacy_main(', s, count=1)
if n != 1:
    raise SystemExit("cannot find/rename main() in legacy.c (or multiple mains)")

p.write_text(s2, encoding="utf-8")
print("OK: legacy.c main renamed to std7_fixed_legacy_main")
PY

  # create wrapper main
  cat > "$WRAP" <<'C'
/* file: src/mkimage/mkimage_std7_fixed.c
 * date: 2026-05-04
 * purpose: wrapper entrypoint for std7_fixed mkimage (calls legacy, later calls modular builder)
 */
int std7_fixed_legacy_main(int argc, char **argv);

int main(int argc, char **argv) {
  return std7_fixed_legacy_main(argc, argv);
}
C
fi

echo "[regen] PASS1 complete."
echo "[regen] IMPORTANT: update Makefile sources:"
echo "  - any binary that compiled src/vm/space.c must also compile src/vm/diag/vmrep.c"
echo "  - mkimage_std7_fixed must compile BOTH:"
echo "      src/mkimage/mkimage_std7_fixed.c (wrapper) AND src/mkimage/std7_fixed/legacy.c"