#!/bin/sh
set -eu

F="src/mkimage/std7_fixed/words_ctrl.c"
test -f "$F"

ts="$(date +%Y%m%d_%H%M%S)"
cp -a "$F" "$F.bak.$ts"
echo "[fix] backup $F -> $F.bak.$ts" >&2

python3 - "$F" <<'PY'
import sys, re
from pathlib import Path

path = Path(sys.argv[1])
s = path.read_text(encoding="utf-8", errors="replace")

def find_func(text: str, name: str):
    m = re.search(rf'^[ \t]*void[ \t]+{re.escape(name)}[ \t]*\(', text, flags=re.M)
    if not m:
        return None
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
                return (m.start(), end)
        i += 1
    raise ValueError(f"no matching '}}' for {name}")

names = ["write_word_add24_micro", "write_word_eq24_micro", "write_word_lt24_micro"]
spans = []
for n in names:
    r = find_func(s, n)
    if r:
        spans.append((r[0], r[1], n))

if not spans:
    print("[fix] no 2a functions found in words_ctrl.c; nothing to do")
    sys.exit(0)

spans.sort(reverse=True)
for a,b,n in spans:
    s = s[:a] + f"/* removed (belongs to 2a module): {n} */\n\n" + s[b:]

path.write_text(s, encoding="utf-8")
print(f"[fix] removed {len(spans)} functions from words_ctrl.c")
PY

echo "[fix] done. Now rebuild:" >&2
echo "  make clean && make" >&2
