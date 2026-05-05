#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_ensure_toktest_makefile"
mkdir -p "$bakdir"

NAME="mktok_test_add24p_via_prims"
SRC="src/tokens/${NAME}.c"
MF="Makefile"

[ -f "$MF" ] || { echo "FAIL: missing $MF" >&2; exit 1; }
[ -f "$SRC" ] || { echo "FAIL: missing $SRC (create the test file first)" >&2; exit 1; }

cp -a "$MF" "$bakdir/Makefile"

if grep -q "$NAME" "$MF"; then
  echo "OK: $MF already mentions $NAME"
  exit 0
fi

# If Makefile uses wildcard/pattern to grab all mktok_test_*.c, we are done.
if grep -Eq 'wildcard[[:space:]]*\(.*src/tokens/mktok_test_\*\.c' "$MF" \
  || grep -Eq 'src/tokens/mktok_test_%\.c' "$MF" \
  || grep -Eq 'mktok_test_%' "$MF"
then
  echo "OK: $MF already uses wildcard/pattern rules for mktok_test_*.c; no edit needed."
  exit 0
fi

tmp="tmp/ensure_toktest_${ts}"
mkdir -p "$tmp"

out="$tmp/Makefile.new"

# Strategy:
# 1) Prefer appending binary name to a list line that already contains mktok_test_... (no .c)
# 2) Otherwise append source path to a list line that contains src/tokens/mktok_test_... .c
# If neither found -> fail with guidance.

awk -v NAME="$NAME" -v SRC="$SRC" '
BEGIN { inserted=0 }

{
  line=$0

  # Case A: a variable/list line contains mktok_test_* words (binary names), but not ".c"
  if (!inserted &&
      line ~ /mktok_test_[A-Za-z0-9_]+/ &&
      line !~ /\.c/ &&
      line ~ /=|:=|\+=/)
  {
    print line " " NAME
    inserted=1
    next
  }

  # Case B: a variable/list line contains src/tokens/mktok_test_*.c
  if (!inserted &&
      line ~ /src\/tokens\/mktok_test_[A-Za-z0-9_]+\.c/ &&
      line ~ /=|:=|\+=/)
  {
    print line " " SRC
    inserted=1
    next
  }

  print line
}

END {
  if (!inserted) exit 2
}
' "$MF" >"$out" || {
  rc=$?
  if [ "$rc" -eq 2 ]; then
    echo "FAIL: could not find token-test list in $MF to append $NAME" >&2
    echo "Hint: your Makefile might generate token tests in a custom way." >&2
    echo "Please paste the part of Makefile that builds mktok_test_* and I will patch it precisely." >&2
    exit 1
  fi
  echo "FAIL: awk error while patching $MF" >&2
  exit 1
}

mv "$out" "$MF"
echo "OK: patched $MF (backup: $bakdir/Makefile)"
echo "Next: run: make test"
