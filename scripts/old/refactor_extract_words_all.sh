#!/bin/sh
set -eu

LEG="src/mkimage/std7_fixed/legacy.c"
OUTC="src/mkimage/std7_fixed/words_all.c"
OUTH="src/mkimage/std7_fixed/words_all.h"

test -f "$LEG"
test ! -f "$OUTC" || { echo "ERROR: $OUTC already exists" >&2; exit 1; }
test ! -f "$OUTH" || { echo "ERROR: $OUTH already exists" >&2; exit 1; }

ts="$(date +%Y%m%d_%H%M%S)"
cp -a "$LEG" "$LEG.bak.$ts"
echo "[extract] backup $LEG -> $LEG.bak.$ts" >&2

python3 - <<'PY'
from pathlib import Path
import re

leg_path = Path("src/mkimage/std7_fixed/legacy.c")
s = leg_path.read_text(encoding="utf-8", errors="replace")

# Extract block: from "static void nop_fill_image" up to before "static void usage"
m0 = re.search(r'^\s*static\s+void\s+nop_fill_image\s*\(', s, flags=re.M)
m1 = re.search(r'^\s*static\s+void\s+usage\s*\(', s, flags=re.M)
if not m0 or not m1 or m1.start() <= m0.start():
    raise SystemExit("cannot locate extraction region: need 'static void nop_fill_image(' and later 'static void usage('")

block = s[m0.start():m1.start()]

# Determine which functions legacy calls directly and must be exported
export_names = [
    "nop_fill_processor",
    "write_next_page",
    "write_word_nop",
    "write_word_setup_echo",
    "write_word_inreq",
    "write_word_outreq",
    "write_word_halt",
    "write_word_saveip",
    "write_word_jmp",
    "write_word_setolen",
    "write_word_ifgot0",
    "write_word_lit_generic",
    "write_word_litip",
    "write_word_copy",
    "write_word_bnot",
    "write_word_band",
    "write_word_bor",
    "write_word_bxor",
    "write_page_branch",
    "write_page_do",
    "write_page_end",
    "write_word_add24_micro",
    "write_word_eq24_micro",
    "write_word_lt24_micro",
    "write_word_eq24p_micro",
    "write_cell",
]

# In extracted block, turn "static void <name>(" into "void <name>(" for exported names
for name in export_names:
    block = re.sub(rf'^\s*static\s+void\s+{name}\s*\(',
                   lambda m: m.group(0).replace("static void", "void", 1),
                   block, flags=re.M)

# Generate header prototypes
protos = []
for name in export_names:
    # crude prototype search: find first function signature line containing "void name("
    mm = re.search(rf'^\s*void\s+{name}\s*\([^;{{]*\)', block, flags=re.M)
    if not mm:
        # maybe the signature spans multiple lines; find from "void name(" to "{"
        mm2 = re.search(rf'^\s*void\s+{name}\s*\([\s\S]*?\)\s*\{{', block, flags=re.M)
        if not mm2:
            raise SystemExit(f"cannot find signature for exported function: {name}")
        sig = mm2.group(0)
        sig = sig[:sig.rfind("{")].rstrip()
    else:
        sig = mm.group(0).rstrip()
    # normalize: ensure ends with ')'
    sig = sig.strip()
    # remove trailing '{' if present
    sig = sig.split("{")[0].strip()
    protos.append(sig + ";")

header = """\
/* file: src/mkimage/std7_fixed/words_all.h
 * date: 2026-05-04
 * purpose: exported builders for std7_fixed pages/words (extracted from legacy.c)
 */
#ifndef STD7_FIXED_WORDS_ALL_H_
#define STD7_FIXED_WORDS_ALL_H_

#include "space.h"

""" + "\n".join(protos) + """

#endif
"""

Path("src/mkimage/std7_fixed/words_all.h").write_text(header, encoding="utf-8")

# Create words_all.c with includes + extracted block
words_c = """\
/* file: src/mkimage/std7_fixed/words_all.c
 * date: 2026-05-04
 * purpose: std7_fixed page/word builders (extracted from legacy.c; transitional module)
 */
#include "words_all.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

""" + block

Path("src/mkimage/std7_fixed/words_all.c").write_text(words_c, encoding="utf-8")

# Patch legacy.c:
#  - insert include "words_all.h" after existing includes if not present
#  - remove extracted block
s2 = s.replace(block, "/* extracted to words_all.c */\n", 1)
if '#include "words_all.h"' not in s2:
    # insert after #include "space.h" (exists in your legacy.c)
    s2 = s2.replace('#include "space.h"\n', '#include "space.h"\n#include "words_all.h"\n', 1)

leg_path.write_text(s2, encoding="utf-8")

print("[extract] OK: created words_all.c/.h and shrunk legacy.c")
PY

echo "[extract] done. Now rebuild+test:" >&2
echo "  make clean && make" >&2
echo "  scripts/tdd/run_all.sh" >&2
echo "  make test" >&2