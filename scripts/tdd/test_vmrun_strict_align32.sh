#!/bin/sh
set -eu

mkdir -p tmp

need_bin() { [ -x "$1" ] || { echo "ERROR: missing binary: $1 (run: make bins)" >&2; exit 1; }; }

need_bin build/bin/mkimage_std7_fixed
need_bin build/bin/forth0c
need_bin build/bin/vmrun
need_bin build/bin/vmprep_forth0

std7="tmp/std7_vmrun_strict_align32.bin"
build/bin/mkimage_std7_fixed --out "$std7" >/dev/null 2>/dev/null

run_case_expect_fail() {
  name="$1"
  f0="$2"
  want="$3"

  tok="tmp/${name}.tok"
  compiled="tmp/${name}_compiled.bin"
  after="tmp/${name}_after.bin"
  err="tmp/${name}_run.stderr"

  build/bin/forth0c --image "$std7" --in "$f0" --out "$tok" 1>/dev/null 2>/dev/null

  build/bin/vmrun --image "$std7" --life 20000000 --dump "$compiled" < "$tok" >/dev/null 2>/dev/null
  build/bin/vmprep_forth0 --image "$compiled" >/dev/null 2>/dev/null

  if COPYSPACE_VM_STRICT_ALIGN32=1 build/bin/vmrun --image "$compiled" --life 20000000 --dump "$after" \
       < /dev/null >/dev/null 2>"$err"
  then
    echo "ERROR: vmrun succeeded, but runtime strict alignment should fail (case: $name)" >&2
    exit 1
  fi

  grep -q "$want" "$err"
}

run_case_expect_fail vmrun_strict_align32_unaligned src/forth0/tests/bad_unaligned_ptr.f0 "not 32-bit aligned"
run_case_expect_fail vmrun_strict_align32_oob      src/forth0/tests/bad_oob_ptr.f0       "out of bounds"
