#!/bin/sh
set -eu
dir="src/mkimage/std7_fixed"
for sym in write_word_add24_micro write_word_eq24_micro write_word_lt24_micro; do
  n="$(grep -R "^[[:space:]]*void[[:space:]]\\+$sym[[:space:]]*(" -n "$dir"/*.c | wc -l | tr -d ' ')"
  if [ "$n" -ne 1 ]; then
    echo "ERROR: expected exactly 1 definition of $sym, got $n" >&2
    grep -R "^[[:space:]]*void[[:space:]]\\+$sym[[:space:]]*(" -n "$dir"/*.c >&2 || true
    exit 1
  fi
done
echo "OK: 2a defs unique"