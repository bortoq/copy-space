#!/bin/sh
set -eu

D="src/mkimage/std7_fixed"

OLD_H="$D/words_all.h"
OLD_C="$D/words_all.c"

NEW_H="$D/words.h"
NEW_C="$D/words_core.c"

test -f "$OLD_H"
test -f "$OLD_C"
test ! -f "$NEW_H" || { echo "ERROR: $NEW_H already exists" >&2; exit 1; }
test ! -f "$NEW_C" || { echo "ERROR: $NEW_C already exists" >&2; exit 1; }

ts="$(date +%Y%m%d_%H%M%S)"
cp -a "$OLD_H" "$OLD_H.bak.$ts"
cp -a "$OLD_C" "$OLD_C.bak.$ts"
echo "[pass2.4c] backup words_all.* -> *.bak.$ts" >&2

# 1) Rename files
mv "$OLD_H" "$NEW_H"
mv "$OLD_C" "$NEW_C"

# 2) Create compatibility shim words_all.h (so any stale include still works)
cat > "$OLD_H" <<'H'
/* file: src/mkimage/std7_fixed/words_all.h
 * date: 2026-05-04
 * purpose: compatibility shim (deprecated). Use "words.h".
 */
#ifndef STD7_FIXED_WORDS_ALL_SHIM_H_
#define STD7_FIXED_WORDS_ALL_SHIM_H_
#include "words.h"
#endif
H

# 3) Update includes in std7_fixed sources to use words.h going forward
# (leave the shim for safety, but clean code should include words.h)
for f in "$D"/*.c "$D"/*.h; do
  [ -f "$f" ] || continue
  sed -i 's/#include "words_all.h"/#include "words.h"/g' "$f"
done

# 4) Ensure header guards/file headers look sane (optional minimal touch)
# (We keep existing content; you can later polish headers.)

echo "[pass2.4c] done. Rebuild+test:" >&2
echo "  make clean && make" >&2
echo "  scripts/tdd/run_all.sh" >&2
echo "  make test" >&2