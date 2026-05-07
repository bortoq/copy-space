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

run_one() { # name f0path expected_hex nbytes
  name="$1"
  f0path="$2"
  expected_hex="$3"
  nbytes="$4"

  std7="tmp/${name}.std7.bin"
  tok="tmp/${name}.tok"
  compiled="tmp/${name}.compiled.bin"
  after="tmp/${name}.after.bin"
  got="tmp/${name}.got.bin"
  expected="tmp/${name}.expected.bin"

  build/bin/mkimage_std7_fixed --out "$std7" >/dev/null 2>"tmp/${name}.mkimage.stderr"

  testg="$(
    build/bin/forth0c --image "$std7" --in "$f0path" --out "$tok" \
      1>/dev/null 2>"tmp/${name}.forth0c.stderr"
    awk -F= '/^TESTG\(byte\)=/{print $2}' "tmp/${name}.forth0c.stderr"
  )"
  test -n "$testg"

  build/bin/vmrun --image "$std7" --life "$LIFE_COMPILE" --dump "$compiled" \
    < "$tok" >/dev/null 2>"tmp/${name}.compile.stderr"

  build/bin/vmprep_forth0 --image "$compiled" >/dev/null 2>"tmp/${name}.prep.stderr"

  build/bin/vmrun --image "$compiled" --life "$LIFE_RUN" --dump "$after" \
    < /dev/null >/dev/null 2>"tmp/${name}.run.stderr"

  dd if="$after" bs=1 skip="$testg" count="$nbytes" status=none > "$got"
  hex_to_bin "$expected_hex" "$expected"

  cmp -s "$got" "$expected"
}

# Padding semantics: LOAD ignores padding; STORE preserves padding
run_one forth0_ptrprims_padding src/forth0/tests/test_ptrprims_padding.f0 "123456abcdefaa" 7

# EQ24P: 80 00 80 00
run_one forth0_eq24p           src/forth0/tests/test_eq24p.f0            "80008000"       4
