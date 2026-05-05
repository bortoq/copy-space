#!/bin/sh
set -eu

D="src/mkimage/std7_fixed"
SRC="$D/words_core.c"

test -f "$SRC"
test -f "$D/words.h"
test -f "$D/words_int.h"

# fail if already split
for f in "$D/words_next.c" "$D/words_ctrl.c" "$D/words_literals.c" "$D/words_copy_mod.c" "$D/words_gates.c"; do
  if [ -f "$f" ]; then
    echo "ERROR: $f already exists (PASS2.5 already applied?)" >&2
    exit 1
  fi
done

ts="$(date +%Y%m%d_%H%M%S)"
cp -a "$SRC" "$SRC.bak.$ts"
echo "[pass2.5] backup $SRC -> $SRC.bak.$ts" >&2

python3 - <<'PY'
from pathlib import Path
import re

src_path = Path("src/mkimage/std7_fixed/words_core.c")
s = src_path.read_text(encoding="utf-8", errors="replace")

def find_func(text: str, name: str):
    m = re.search(rf'^[ \t]*void[ \t]+{re.escape(name)}[ \t]*\(', text, flags=re.M)
    if not m:
        raise KeyError(name)
    brace = text.find("{", m.start())
    if brace < 0:
        raise ValueError(f"no '{{' for {name}")

    i = brace
    depth = 0
    in_str = in_chr = in_sl = in_ml = False
    esc = False
    while i < len(text):
        c = text[i]
        n = text[i+1] if i+1 < len(text) else ""
        if in_sl:
            if c == "\n": in_sl = False
            i += 1; continue
        if in_ml:
            if c == "*" and n == "/":
                in_ml = False; i += 2; continue
            i += 1; continue
        if in_str:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': in_str = False
            i += 1; continue
        if in_chr:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == "'": in_chr = False
            i += 1; continue

        if c == "/" and n == "/":
            in_sl = True; i += 2; continue
        if c == "/" and n == "*":
            in_ml = True; i += 2; continue
        if c == '"':
            in_str = True; i += 1; continue
        if c == "'":
            in_chr = True; i += 1; continue

        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                # eat trailing whitespace/newlines
                while end < len(text) and text[end] in " \t\r\n":
                    end += 1
                return m.start(), end
        i += 1

    raise ValueError(f"no matching '}}' for {name}")

def extract(names):
    global s
    spans = []
    for n in names:
        a,b = find_func(s, n)
        spans.append((a,b,n))
    spans.sort(reverse=True)

    bodies = []
    for a,b,n in spans:
        bodies.append((n, s[a:b]))
        s = s[:a] + f"/* moved: {n} */\n\n" + s[b:]
    bodies.reverse()
    return [body for _,body in bodies]

groups = [
    ("src/mkimage/std7_fixed/words_next.c",
     "NEXT page builder extracted from words_core.c",
     ["write_next_page"]),

    ("src/mkimage/std7_fixed/words_ctrl.c",
     "control/basic words extracted from words_core.c",
     [
       "write_word_nop",
       "write_word_setup_echo",
       "write_word_inreq",
       "write_word_outreq",
       "write_word_halt",
       "write_word_saveip",
       "write_word_jmp",
       "write_word_setolen",
       "write_word_ifgot0",
     ]),

    ("src/mkimage/std7_fixed/words_literals.c",
     "literal-related words extracted from words_core.c",
     [
       "write_word_lit_generic",
       "write_word_litip",
     ]),

    ("src/mkimage/std7_fixed/words_copy_mod.c",
     "COPY word extracted from words_core.c",
     [
       "write_word_copy",
     ]),

    ("src/mkimage/std7_fixed/words_gates.c",
     "bitwise gate words extracted from words_core.c",
     [
       "write_word_bnot",
       "write_word_band",
       "write_word_bor",
       "write_word_bxor",
     ]),
]

def write_unit(path, purpose, bodies):
    Path(path).write_text(
f"""/* file: {path}
 * date: 2026-05-04
 * purpose: {purpose}
 */
#include "words.h"
#include "words_int.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>

""" + "\n\n".join(bodies) + "\n",
        encoding="utf-8"
    )

for path, purpose, names in groups:
    bodies = extract(names)
    write_unit(path, purpose, bodies)

# Patch words_core.c: keep includes, leave moved markers
src_path.write_text(s, encoding="utf-8")
print("[pass2.5] OK: split words_core.c into words_next/ctrl/literals/copy/gates")
PY

echo "[pass2.5] done. Rebuild+test:" >&2
echo "  make clean && make" >&2
echo "  scripts/tdd/run_all.sh" >&2
echo "  make test" >&2