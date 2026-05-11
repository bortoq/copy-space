#!/bin/sh
set -eu

mkdir -p tmp

need_bin() { [ -x "$1" ] || { echo "ERROR: missing binary: $1 (run: make bins)" >&2; exit 1; }; }

need_bin build/bin/mkimage_std7_fixed
need_bin build/bin/forth0c
need_bin build/bin/vmrun
need_bin build/bin/vmprep_forth0

std7="tmp/std7_vmrun_strict_align32.bin"
tok="tmp/vmrun_strict_align32_bad.tok"
compiled="tmp/vmrun_strict_align32_compiled.bin"
after="tmp/vmrun_strict_align32_after.bin"
err="tmp/vmrun_strict_align32_run.stderr"

build/bin/mkimage_std7_fixed --out "$std7" >/dev/null 2>/dev/null

build/bin/forth0c --image "$std7" --in src/forth0/tests/bad_unaligned_ptr.f0 --out "$tok" \
  1>/dev/null 2>/dev/null

build/bin/vmrun --image "$std7" --life 20000000 --dump "$compiled" \
  < "$tok" >/dev/null 2>/dev/null

build/bin/vmprep_forth0 --image "$compiled" >/dev/null 2>/dev/null

if COPYSPACE_VM_STRICT_ALIGN32=1 build/bin/vmrun --image "$compiled" --life 20000000 --dump "$after" \
     < /dev/null >/dev/null 2>"$err"
then
  echo "ERROR: vmrun succeeded, but runtime strict alignment should fail" >&2
  exit 1
fi

grep -q "not 32-bit aligned" "$err"
