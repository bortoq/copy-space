#!/bin/sh
set -eu

# run from repo root
test -f Makefile || { echo "ERROR: run from repo root (Makefile not found)"; exit 1; }

DIR="src/mkimage/std7_fixed"
SRC="$DIR/words_2a.c"

ADD="$DIR/words_add24.c"
EQ="$DIR/words_eq24.c"
LT="$DIR/words_lt24.c"

test -f "$SRC"
test ! -e "$ADD" || { echo "ERROR: $ADD already exists"; exit 1; }
test ! -e "$EQ"  || { echo "ERROR: $EQ already exists"; exit 1; }
test ! -e "$LT"  || { echo "ERROR: $LT already exists"; exit 1; }

sym_check_one_in_file () {
  sym="$1"
  want="$2"
  # find definitions only in *.c
  hits="$(grep -R "^[[:space:]]*void[[:space:]]\+$sym[[:space:]]*(" -n "$DIR"/*.c 2>/dev/null || true)"
  n="$(printf "%s\n" "$hits" | sed '/^$/d' | wc -l | tr -d ' ')"
  if [ "$n" -ne 1 ]; then
    echo "ERROR: expected exactly 1 definition of $sym in $DIR/*.c, got $n" >&2
    printf "%s\n" "$hits" >&2
    exit 1
  fi
  case "$hits" in
    "$want"*) : ;;
    *)
      echo "ERROR: $sym is not defined in expected file $want" >&2
      echo "got: $hits" >&2
      exit 1
      ;;
  esac
}

echo "[split2a] precheck unique defs (must be only in words_2a.c)" >&2
sym_check_one_in_file write_word_add24_micro "$SRC:"
sym_check_one_in_file write_word_eq24_micro  "$SRC:"
sym_check_one_in_file write_word_lt24_micro  "$SRC:"

ts="$(date +%Y%m%d_%H%M%S)"
cp -a "$SRC" "$SRC.bak.$ts"
echo "[split2a] backup $SRC -> $SRC.bak.$ts" >&2

python3 - <<'PY'
from pathlib import Path
import re, sys

SRC = Path("src/mkimage/std7_fixed/words_2a.c")
text = SRC.read_text(encoding="utf-8", errors="replace")

def find_func(t: str, name: str):
    # allow optional "static"
    m = re.search(rf'^[ \t]*(?:static\s+)?void[ \t]+{re.escape(name)}[ \t]*\(', t, flags=re.M)
    if not m:
        raise SystemExit(f"cannot find function header for {name}")
    brace = t.find("{", m.start())
    if brace < 0:
        raise SystemExit(f"cannot find '{{' for {name}")

    i = brace
    depth = 0
    in_str = in_chr = in_sl = in_ml = False
    esc = False
    while i < len(t):
        c = t[i]
        n = t[i+1] if i+1 < len(t) else ""
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
                while end < len(t) and t[end] in " \t\r\n":
                    end += 1
                return m.start(), end
        i += 1
    raise SystemExit(f"brace match failed for {name}")

def extract(name: str):
    global text
    a,b = find_func(text, name)
    body = text[a:b]
    text = text[:a] + f"/* moved to separate file: {name} */\n\n" + text[b:]
    return body

add = extract("write_word_add24_micro")
eq  = extract("write_word_eq24_micro")
lt  = extract("write_word_lt24_micro")

def write_unit(path: str, purpose: str, body: str):
    Path(path).write_text(f"""\
/* file: {path}
 * date: 2026-05-04
 * purpose: {purpose}
 */
#include "words.h"
#include "words_int.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>

{body}
""", encoding="utf-8")

write_unit("src/mkimage/std7_fixed/words_add24.c",
           "2a microcode builder: ADD24 (extracted from words_2a.c)",
           add)
write_unit("src/mkimage/std7_fixed/words_eq24.c",
           "2a microcode builder: EQ24 (extracted from words_2a.c)",
           eq)
write_unit("src/mkimage/std7_fixed/words_lt24.c",
           "2a microcode builder: LT24 (extracted from words_2a.c)",
           lt)

SRC.write_text(text, encoding="utf-8")
print("[split2a] wrote new files and trimmed words_2a.c")
PY

# force flush (helpful on flash media)
sync || true

# post-check: new files exist
test -f "$ADD"
test -f "$EQ"
test -f "$LT"

echo "[split2a] created:" >&2
ls -lh "$ADD" "$EQ" "$LT" >&2

echo "[split2a] postcheck unique defs (must be in new files)" >&2
sym_check_one_in_file write_word_add24_micro "$ADD:"
sym_check_one_in_file write_word_eq24_micro  "$EQ:"
sym_check_one_in_file write_word_lt24_micro  "$LT:"

echo "[split2a] OK" >&2