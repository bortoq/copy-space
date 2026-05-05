#!/bin/sh
set -eu

WALL="src/mkimage/std7_fixed/words_all.c"
TOK="src/mkimage/std7_fixed/words_tokcomp.c"
W2A="src/mkimage/std7_fixed/words_2a.c"
W2B="src/mkimage/std7_fixed/words_2b.c"

test -f "$WALL"
test -f "src/mkimage/std7_fixed/words_all.h"
test -f "src/mkimage/std7_fixed/words_int.h"

test ! -f "$TOK" || { echo "ERROR: $TOK already exists" >&2; exit 1; }
test ! -f "$W2A" || { echo "ERROR: $W2A already exists" >&2; exit 1; }
test ! -f "$W2B" || { echo "ERROR: $W2B already exists" >&2; exit 1; }

ts="$(date +%Y%m%d_%H%M%S)"
cp -a "$WALL" "$WALL.bak.$ts"
echo "[split] backup $WALL -> $WALL.bak.$ts" >&2

python3 - <<'PY'
from pathlib import Path
import re

src_path = Path("src/mkimage/std7_fixed/words_all.c")
s = src_path.read_text(encoding="utf-8", errors="replace")

def find_func(text: str, name: str):
    # find "void name(" at line start (possibly with spaces)
    m = re.search(rf'^[ \t]*void[ \t]+{re.escape(name)}[ \t]*\(', text, flags=re.M)
    if not m:
        raise KeyError(name)

    # find '{' after signature
    brace = text.find("{", m.start())
    if brace < 0:
        raise ValueError(f"no '{{' for {name}")

    # brace match (simple, but good enough for our generated C)
    i = brace
    depth = 0
    in_str = False
    in_chr = False
    in_sl = False
    in_ml = False
    esc = False
    while i < len(text):
        c = text[i]
        n = text[i+1] if i+1 < len(text) else ""

        if in_sl:
            if c == "\n":
                in_sl = False
            i += 1
            continue
        if in_ml:
            if c == "*" and n == "/":
                in_ml = False
                i += 2
                continue
            i += 1
            continue
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if in_chr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == "'":
                in_chr = False
            i += 1
            continue

        if c == "/" and n == "/":
            in_sl = True
            i += 2
            continue
        if c == "/" and n == "*":
            in_ml = True
            i += 2
            continue
        if c == '"':
            in_str = True
            i += 1
            continue
        if c == "'":
            in_chr = True
            i += 1
            continue

        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                # include trailing whitespace/newlines up to next blank line
                while end < len(text) and text[end] in " \t\r\n":
                    # stop if we consumed 2 newlines already? keep it simple: consume all whitespace
                    end += 1
                return m.start(), end

        i += 1

    raise ValueError(f"no matching '}}' for {name}")

def extract_many(names):
    global s
    extracted = []
    # remove from end to start to keep indices stable
    spans = []
    for n in names:
        a,b = find_func(s, n)
        spans.append((a,b,n))
    spans.sort(reverse=True)

    for a,b,n in spans:
        extracted.append((n, s[a:b]))
        s = s[:a] + f"/* moved: {n} */\n\n" + s[b:]
    extracted.reverse()
    return [body for _,body in extracted]

tok_names = ["write_page_branch", "write_page_do", "write_page_end"]
a2_names  = ["write_word_add24_micro", "write_word_eq24_micro", "write_word_lt24_micro"]
b2_names  = ["write_word_eq24p_micro"]

tok_bodies = extract_many(tok_names)
a2_bodies  = extract_many(a2_names)
b2_bodies  = extract_many(b2_names)

def write_unit(path, purpose, bodies):
    Path(path).write_text(
f"""/* file: {path}
 * date: 2026-05-04
 * purpose: {purpose}
 */
#include "words_all.h"
#include "words_int.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>

""" + "\n\n".join(bodies) + "\n",
        encoding="utf-8"
    )

write_unit("src/mkimage/std7_fixed/words_tokcomp.c",
           "token compiler pages (DO/END/BRANCH) extracted from words_all.c",
           tok_bodies)

write_unit("src/mkimage/std7_fixed/words_2a.c",
           "2a microcode builders (ADD24/EQ24/LT24) extracted from words_all.c",
           a2_bodies)

write_unit("src/mkimage/std7_fixed/words_2b.c",
           "2b microcode builder (EQ24P) extracted from words_all.c",
           b2_bodies)

src_path.write_text(s, encoding="utf-8")
print("[split] OK: created words_tokcomp.c, words_2a.c, words_2b.c and trimmed words_all.c")
PY

echo "[split] done. rebuild+test:" >&2
echo "  make clean && make" >&2
echo "  scripts/tdd/run_all.sh" >&2
echo "  make test" >&2