#!/usr/bin/env bash
set -euo pipefail

LIFE_COMPILE="${LIFE_COMPILE:-20000000}"
LIFE_RUN="${LIFE_RUN:-20000000}"

mkdir -p tmp

# Expect binaries already built by `make tdd`, but be defensive:
if [[ ! -x build/bin/mkimage_std7_fixed || ! -x build/bin/vmrun || ! -x build/bin/vmprep_forth0 ]]; then
  echo "ERROR: binaries not built. Run: make bins" >&2
  exit 1
fi

dump_or_xxd() {
  local f="$1"
  if command -v hexdump >/dev/null 2>&1; then
    hexdump -Cv "$f"
  else
    xxd "$f"
  fi
}

hex_to_bin() { # $1=hexstring $2=outfile
  python3 - "$1" "$2" <<'PY'
import sys
hexs = sys.argv[1].replace(" ", "").replace("\n", "")
out  = sys.argv[2]
open(out, "wb").write(bytes.fromhex(hexs))
PY
}

run_one() { # name expected_hex nbytes
  local name="$1"
  local expected_hex="$2"
  local nbytes="$3"

  local std7="tmp/std7_ptrprims.bin"
  local tok="tmp/${name}.tok.bin"
  local compiled="tmp/${name}.compiled.bin"
  local after="tmp/${name}.after.bin"
  local got="tmp/${name}.got.bin"
  local expected="tmp/${name}.expected.bin"

  # rebuild base image each time? no, but cheap and keeps test isolated
  build/bin/mkimage_std7_fixed --out "$std7" >/dev/null 2>"tmp/${name}.mkimage.stderr"

  local testg
  testg="$(
    "build/bin/${name}" --image "$std7" --out "$tok" \
      1>/dev/null 2>"tmp/${name}.mktok.stderr"
    awk -F= '/^TESTG\(byte\)=/{print $2}' "tmp/${name}.mktok.stderr"
  )"
  test -n "$testg"

  build/bin/vmrun --image "$std7" --life "$LIFE_COMPILE" --dump "$compiled" \
    < "$tok" > /dev/null 2>"tmp/${name}.compile.stderr"

  build/bin/vmprep_forth0 --image "$compiled" > /dev/null 2>"tmp/${name}.prep.stderr"

  build/bin/vmrun --image "$compiled" --life "$LIFE_RUN" --dump "$after" \
    < /dev/null > /dev/null 2>"tmp/${name}.run.stderr"

  dd if="$after" bs=1 skip="$testg" count="$nbytes" status=none > "$got"
  hex_to_bin "$expected_hex" "$expected"

  if cmp -s "$got" "$expected"; then
    echo "PASS: $name"
  else
    echo "FAIL: $name" >&2
    echo "TESTG(byte)=$testg" >&2
    echo "--- got ---" >&2
    dump_or_xxd "$got" >&2
    echo "--- expected ---" >&2
    dump_or_xxd "$expected" >&2
    exit 1
  fi
}

# ADD24 via pointer primitives (matches mktok_test_add24.c layout)
run_one \
  mktok_test_add24p_via_prims \
  "00000000000000000000000000000000
   ffffff00000001000000000080000000
   12345600010203001336590000000000
   80000000800000000000000080000000" \
  64

# LT24 via pointer primitives: bytes [00,00,80,00]
run_one \
  mktok_test_lt24p_via_prims \
  "00008000" \
  4

# EQ24P word: bytes [80,00,80,00]
run_one \
  mktok_test_eq24p \
  "80008000" \
  4

# Explicit pointer arithmetic test: AP, AP+32, AP+64 (each 24-bit big-endian)
run_one \
  mktok_test_incptr32 \
  "0000e0000100000120" \
  9

# Derived ADD_PTR_CONST32 test: start, +1 block, +7 blocks (cumulative)
run_one \
  mktok_test_addptr_const32 \
  "00ffe00100000100e0" \
  9
