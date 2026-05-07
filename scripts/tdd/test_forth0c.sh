#!/bin/sh
set -eu

LIFE_COMPILE="${LIFE_COMPILE:-20000000}"
LIFE_RUN="${LIFE_RUN:-20000000}"

mkdir -p tmp

need_bin() {
  test -x "$1" || { echo "ERROR: missing binary: $1" >&2; exit 1; }
}

need_bin build/bin/mkimage_std7_fixed
need_bin build/bin/forth0c
need_bin build/bin/vmrun
need_bin build/bin/vmprep_forth0

std7="tmp/std7_forth0c.bin"
tok="tmp/forth0c_smoke.tok"
compiled="tmp/forth0c_smoke.compiled.bin"
after="tmp/forth0c_smoke.after.bin"
got="tmp/forth0c_smoke.got.bin"
expected="tmp/forth0c_smoke.expected.bin"

build/bin/mkimage_std7_fixed --out "$std7" >/dev/null 2>tmp/forth0c.mkimage.stderr

testg="$(
  build/bin/forth0c --image "$std7" --in src/forth0/tests/smoke_include.f0 --out "$tok" \
    1>/dev/null 2>tmp/forth0c.stderr
  awk -F= '/^TESTG\(byte\)=/{print $2}' tmp/forth0c.stderr
)"
test -n "$testg"

build/bin/vmrun --image "$std7" --life "$LIFE_COMPILE" --dump "$compiled" \
  < "$tok" >/dev/null 2>tmp/forth0c.compile.stderr

build/bin/vmprep_forth0 --image "$compiled" >/dev/null 2>tmp/forth0c.prep.stderr

build/bin/vmrun --image "$compiled" --life "$LIFE_RUN" --dump "$after" \
  < /dev/null >/dev/null 2>tmp/forth0c.run.stderr

dd if="$after" bs=1 skip="$testg" count=2 status=none > "$got"
python3 - "$expected" <<'PY'
import sys
open(sys.argv[1], "wb").write(bytes.fromhex("80aa"))
PY

cmp -s "$got" "$expected"
