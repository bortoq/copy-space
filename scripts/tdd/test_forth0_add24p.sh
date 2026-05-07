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

hex_to_bin() { # $1=hexstring $2=outfile
  python3 - "$1" "$2" <<'PY'
import sys
hexs = sys.argv[1].replace(" ", "").replace("\n", "")
out  = sys.argv[2]
open(out, "wb").write(bytes.fromhex(hexs))
PY
}

std7="tmp/std7_forth0_add24p.bin"
tok="tmp/forth0_add24p.tok"
compiled="tmp/forth0_add24p.compiled.bin"
after="tmp/forth0_add24p.after.bin"
got="tmp/forth0_add24p.got.bin"
expected="tmp/forth0_add24p.expected.bin"

build/bin/mkimage_std7_fixed --out "$std7" >/dev/null 2>tmp/forth0_add24p.mkimage.stderr

testg="$(
  build/bin/forth0c --image "$std7" --in src/forth0/tests/test_add24p_via_prims.f0 --out "$tok" \
    1>/dev/null 2>tmp/forth0_add24p.forth0c.stderr
  awk -F= '/^TESTG\(byte\)=/{print $2}' tmp/forth0_add24p.forth0c.stderr
)"
test -n "$testg"

build/bin/vmrun --image "$std7" --life "$LIFE_COMPILE" --dump "$compiled" \
  < "$tok" >/dev/null 2>tmp/forth0_add24p.compile.stderr

build/bin/vmprep_forth0 --image "$compiled" >/dev/null 2>tmp/forth0_add24p.prep.stderr

build/bin/vmrun --image "$compiled" --life "$LIFE_RUN" --dump "$after" \
  < /dev/null >/dev/null 2>tmp/forth0_add24p.run.stderr

dd if="$after" bs=1 skip="$testg" count=64 status=none > "$got"

# Expected 4x32 bytes (same as mktok_test_add24p_via_prims.c)
python3 - "$expected" <<'PY'
import sys
hexs = (
    "00000000000000000000000000000000"
    "ffffff00000001000000000080000000"
    "12345600010203001336590000000000"
    "80000000800000000000000080000000"
)
open(sys.argv[1], "wb").write(bytes.fromhex(hexs))
PY

cmp -s "$got" "$expected"
