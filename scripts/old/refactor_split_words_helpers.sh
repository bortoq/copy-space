#!/bin/sh
set -eu

WALL="src/mkimage/std7_fixed/words_all.c"
HINT="src/mkimage/std7_fixed/words_int.h"
HELP="src/mkimage/std7_fixed/words_helpers.c"

test -f "$WALL"
test ! -f "$HELP" || { echo "ERROR: $HELP already exists" >&2; exit 1; }
test ! -f "$HINT" || { echo "ERROR: $HINT already exists" >&2; exit 1; }

ts="$(date +%Y%m%d_%H%M%S)"
cp -a "$WALL" "$WALL.bak.$ts"
echo "[split] backup $WALL -> $WALL.bak.$ts" >&2

python3 - <<'PY'
from pathlib import Path
import re, sys

wall = Path("src/mkimage/std7_fixed/words_all.c")
s = wall.read_text(encoding="utf-8", errors="replace")

# Find boundaries:
# helpers start at first "static void nop_fill_image"
m0 = re.search(r'^\s*static\s+void\s+nop_fill_image\s*\(', s, flags=re.M)
if not m0:
    raise SystemExit("cannot find 'static void nop_fill_image(' in words_all.c")

# helpers end just before the "NEXT and std7 words" section header
marker = "/* ---------- NEXT and std7 words ---------- */"
m1 = s.find(marker)
if m1 < 0 or m1 <= m0.start():
    raise SystemExit("cannot find marker '/* ---------- NEXT and std7 words ---------- */' after helpers")

helpers = s[m0.start():m1]

# Convert required helper functions from static to extern (remove 'static ')
# We export these for use by the remaining code in words_all.c
repl_map = [
    (r'^\s*static\s+void\s+nop_fill_image\s*\(',    r'void nop_fill_image('),
    (r'^\s*static\s+void\s+nop_fill_processor\s*\(', r'void nop_fill_processor('),
    (r'^\s*static\s+void\s+write_chain_load\s*\(',   r'void write_chain_load('),
    (r'^\s*static\s+void\s+write_word_return_to_next\s*\(', r'void write_word_return_to_next('),
    (r'^\s*static\s+void\s+write_cell\s*\(',         r'void write_cell('),

    (r'^\s*static\s+bitaddr_t\s+n_lsb_of_slot\s*\(', r'bitaddr_t n_lsb_of_slot('),

    (r'^\s*static\s+void\s+emit_band\s*\(', r'void emit_band('),
    (r'^\s*static\s+void\s+emit_bor\s*\(',  r'void emit_bor('),
    (r'^\s*static\s+void\s+emit_bnot\s*\(', r'void emit_bnot('),
    (r'^\s*static\s+void\s+emit_bxor\s*\(', r'void emit_bxor('),
]

for pat, rep in repl_map:
    helpers = re.sub(pat, rep, helpers, flags=re.M)

# Write words_int.h
Path("src/mkimage/std7_fixed/words_int.h").write_text("""\
/* file: src/mkimage/std7_fixed/words_int.h
 * date: 2026-05-04
 * purpose: internal helpers shared by std7_fixed word/page builders
 */
#ifndef STD7_FIXED_WORDS_INT_H_
#define STD7_FIXED_WORDS_INT_H_

#include "space.h"

/* image/page utils */
void nop_fill_image(vm_t *vm, bitaddr_t img_base);
void nop_fill_processor(vm_t *vm);
void write_chain_load(vm_t *vm, bitaddr_t img, bitaddr_t next_img);
void write_word_return_to_next(vm_t *vm, bitaddr_t word_img, bitaddr_t next_img);
void write_cell(vm_t *vm, bitaddr_t cell_base, bitaddr_t code_ptr, bitaddr_t next_ptr);

/* bool-op helpers used inside pages */
bitaddr_t n_lsb_of_slot(vm_t *vm, unsigned slot);

void emit_band(vm_t *vm, bitaddr_t img, unsigned *pslot,
               bitaddr_t BA, bitaddr_t BB, bitaddr_t R,
               bitaddr_t CONST0);

void emit_bor(vm_t *vm, bitaddr_t img, unsigned *pslot,
              bitaddr_t BA, bitaddr_t BB, bitaddr_t R,
              bitaddr_t CONST1, bitaddr_t CONST0);

void emit_bnot(vm_t *vm, bitaddr_t img, unsigned *pslot,
               bitaddr_t BA, bitaddr_t R,
               bitaddr_t CONST1, bitaddr_t CONST0);

void emit_bxor(vm_t *vm, bitaddr_t img, unsigned *pslot,
               bitaddr_t BA, bitaddr_t BB, bitaddr_t R,
               bitaddr_t X0, bitaddr_t X1,
               bitaddr_t CONST1, bitaddr_t CONST0);

#endif
""", encoding="utf-8")

# Write words_helpers.c (includes words_int.h and contains helper implementations)
Path("src/mkimage/std7_fixed/words_helpers.c").write_text("""\
/* file: src/mkimage/std7_fixed/words_helpers.c
 * date: 2026-05-04
 * purpose: helper functions extracted from words_all.c (page utils + boolean emitters)
 */
#include "words_int.h"
#include <stdint.h>

""" + helpers, encoding="utf-8")

# Patch words_all.c: remove helper block and include words_int.h
s2 = s.replace(s[m0.start():m1], "/* helpers moved to words_helpers.c */\n\n", 1)

if '#include "words_int.h"' not in s2:
    # put after #include "words_all.h"
    s2 = s2.replace('#include "words_all.h"\n', '#include "words_all.h"\n#include "words_int.h"\n', 1)

wall.write_text(s2, encoding="utf-8")
print("[split] OK: created words_int.h + words_helpers.c, trimmed words_all.c")
PY

echo "[split] done. rebuild+test:" >&2
echo "  make clean && make" >&2
echo "  scripts/tdd/run_all.sh" >&2
echo "  make test" >&2