#!/bin/sh
set -eu

mkdir -p tmp

test -x build/bin/mkimage_std7_fixed
test -x build/bin/forth0c

std7="tmp/std7_forth0c_strict.bin"
tok="tmp/forth0c_strict_bad.tok"
err="tmp/forth0c_strict.stderr"

build/bin/mkimage_std7_fixed --out "$std7" >/dev/null 2>/dev/null

# Must fail (non-zero) in strict mode
if F0C_STRICT_ALIGN32=1 build/bin/forth0c --image "$std7" --in src/forth0/tests/bad_unaligned_ptr.f0 --out "$tok" \
     1>/dev/null 2>"$err"
then
  echo "ERROR: forth0c succeeded, but strict alignment should fail" >&2
  exit 1
fi

# Ensure error mentions alignment
grep -q "not 32-bit aligned" "$err"
