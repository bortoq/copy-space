#!/bin/sh
set -eu

D="src/mkimage/std7_fixed"
SRC="$D/words_core.c"

test -f "$SRC"
test -f "$D/words.h"
test -f "$D/words_int.h"

OUT_IF="$D/words_ifgot0.c"
OUT_TC="$D/words_tokcomp.c"
OUT_2A="$D/words_2a.c"

for f in "$OUT_IF" "$OUT_TC" "$OUT_2A"; do
  if [ -f "$f" ]; then
    echo "ERROR: $f already exists; abort (to avoid duplicates)" >&2
    exit 1
  fi
done

ts="$(date +%Y%m%d_%H%M%S)"
cp -a "$SRC" "$SRC.bak.$ts"
echo "[extract] backup $SRC -> $SRC.bak.$ts" >&2

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
                while end < len(text) and text[end] in " \t\r\n":
                    end += 1
                return m.start(), end
        i += 1
    raise ValueError(f"no matching '}}' for {name}")

def extract_many(names):
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

# what to extract
ifgot0_names = ["write_word_ifgot0"]
tokcomp_names = ["write_page_branch", "write_page_do", "write_page_end"]
w2a_names = ["write_word_add24_micro", "write_word_eq24_micro", "write_word_lt24_micro"]

if_bodies = extract_many(ifgot0_names)
tc_bodies = extract_many(tokcomp_names)
a2_bodies = extract_many(w2a_names)

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

write_unit("src/mkimage/std7_fixed/words_ifgot0.c",
           "IFGOT0 word extracted from words_core.c",
           if_bodies)

write_unit("src/mkimage/std7_fixed/words_tokcomp.c",
           "token compiler pages (DO/END/BRANCH) extracted from words_core.c",
           tc_bodies)

write_unit("src/mkimage/std7_fixed/words_2a.c",
           "2a microcode builders (ADD24/EQ24/LT24) extracted from words_core.c",
           a2_bodies)

# Optional: remove stale markers that refer to already split functions (keep file clean)
# Not strictly necessary; commented out to avoid surprises.
# s = re.sub(r'^\s*/\*\s*moved:.*\*/\s*\n', '', s, flags=re.M)

src_path.write_text(s, encoding="utf-8")
print("[extract] OK: wrote words_ifgot0.c, words_tokcomp.c, words_2a.c; trimmed words_core.c")
PY

echo "[extract] done. Now rebuild+test:" >&2
echo "  make clean && make" >&2
echo "  scripts/tdd/run_all.sh" >&2
echo "  make test" >&2