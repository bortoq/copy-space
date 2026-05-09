#!/bin/sh
set -eu

LIFE_COMPILE="${LIFE_COMPILE:-20000000}"
LIFE_RUN="${LIFE_RUN:-20000000}"

mkdir -p tmp

need_bin() { test -x "$1" || { echo "ERROR: missing binary: $1" >&2; exit 1; }; }

need_bin build/bin/mkimage_std7_fixed
need_bin build/bin/forth0c
need_bin build/bin/vmrun
need_bin build/bin/vmprep_forth0

std7="tmp/std7_forth0_lt24p.bin"
tok="tmp/forth0_lt24p.tok"
compiled="tmp/forth0_lt24p.compiled.bin"
after="tmp/forth0_lt24p.after.bin"
got="tmp/forth0_lt24p.got.bin"
expected="tmp/forth0_lt24p.expected.bin"

build/bin/mkimage_std7_fixed --out "$std7" >/dev/null 2>tmp/forth0_lt24p.mkimage.stderr

testg="$(
  build/bin/forth0c --image "$std7" --in src/forth0/tests/test_lt24p_via_prims.f0 --out "$tok" \
    1>/dev/null 2>tmp/forth0_lt24p.forth0c.stderr
  awk -F= '/^TESTG\(byte\)=/{print $2}' tmp/forth0_lt24p.forth0c.stderr
)"
test -n "$testg"

build/bin/vmrun --image "$std7" --life "$LIFE_COMPILE" --dump "$compiled" \
  < "$tok" >/dev/null 2>tmp/forth0_lt24p.compile.stderr

build/bin/vmprep_forth0 --image "$compiled" >/dev/null 2>tmp/forth0_lt24p.prep.stderr

build/bin/vmrun --image "$compiled" --life "$LIFE_RUN" --dump "$after" \
  < /dev/null >/dev/null 2>tmp/forth0_lt24p.run.stderr

dd if="$after" bs=1 skip="$testg" count=4 status=none > "$got"
python3 - "$expected" <<'PY'
import sys
open(sys.argv[1], "wb").write(bytes.fromhex("00008000"))
PY

cmp -s "$got" "$expected"
