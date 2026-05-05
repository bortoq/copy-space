#!/bin/sh
set -euo pipefail

D="src/mkimage/std7_fixed"
SRC="$D/words_2a.c"

OUT_ADD="$D/words_add24.c"
OUT_EQ="$D/words_eq24.c"
OUT_LT="$D/words_lt24.c"

test -f "$SRC"
test -f "$D/words.h"
test -f "$D/words_int.h"

for f in "$OUT_ADD" "$OUT_EQ" "$OUT_LT"; do
  if [ -e "$f" ]; then
    echo "ERROR: $f already exists" >&2
    exit 1
  fi
done

ts="$(date +%Y%m%d_%H%M%S)"
cp -a "$SRC" "$SRC.bak.$ts"
echo "[split2a] backup $SRC -> $SRC.bak.$ts" >&2

python3 - <<'PY'
from pathlib import Path
import re, sys

src_path = Path("src/mkimage/std7_fixed/words_2a.c")
s = src_path.read_text(encoding="utf-8", errors="replace")

def find_func(text: str, name: str):
    # accept both "void name(" and "static void name("
    m = re.search(rf'^[ \t]*(?:static\s+)?void[ \t]+{re.escape(name)}[ \t]*\(', text, flags=re.M)
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
                while end < len(text) and text[end] in " \t\r\n":
                    end += 1
                return m.start(), end
        i += 1
    raise ValueError(f"no matching '}}' for {name}")

def extract_one(name: str):
    global s
    a,b = find_func(s, name)
    body = s[a:b]
    s = s[:a] + f"/* moved: {name} */\n\n" + s[b:]
    return body

names = [
    "write_word_add24_micro",
    "write_word_eq24_micro",
    "write_word_lt24_micro",
]

for n in names:
    if n not in s:
        # cheap hint for debug
        sys.stderr.write(f"[split2a] hint: substring '{n}' not found in file\n")

add_body = extract_one("write_word_add24_micro")
eq_body  = extract_one("write_word_eq24_micro")
lt_body  = extract_one("write_word_lt24_micro")

def write_unit(path, purpose, body):
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

{body}
""",
        encoding="utf-8"
    )

write_unit("src/mkimage/std7_fixed/words_add24.c",
           "2a microcode builder: ADD24 (extracted from words_2a.c)",
           add_body)

write_unit("src/mkimage/std7_fixed/words_eq24.c",
           "2a microcode builder: EQ24 (extracted from words_2a.c)",
           eq_body)

write_unit("src/mkimage/std7_fixed/words_lt24.c",
           "2a microcode builder: LT24 (extracted from words_2a.c)",
           lt_body)

src_path.write_text(s, encoding="utf-8")
print("[split2a] wrote words_add24.c, words_eq24.c, words_lt24.c; trimmed words_2a.c")
PY

# hard checks
test -f "$OUT_ADD"
test -f "$OUT_EQ"
test -f "$OUT_LT"

echo "[split2a] created:"
ls -lh "$OUT_ADD" "$OUT_EQ" "$OUT_LT" >&2
echo "[split2a] new words_2a.c lines:"
wc -l "$SRC" >&2