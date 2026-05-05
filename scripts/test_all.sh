#!/bin/sh
set -eu

SPACE_BYTES="${SPACE_BYTES:-524288}"
PROCESSOR_N="${PROCESSOR_N:-64}"
LIFE_COMPILE="${LIFE_COMPILE:-20000000}"
LIFE_RUN="${LIFE_RUN:-20000000}"
POOL_SMALL="${POOL_SMALL:-4096}"
POOL_BIG="${POOL_BIG:-32768}"

BIN_DIR="build/bin"
OUT_DIR="out"
TMP_DIR="tmp"
FAIL_DIR="$TMP_DIR/fail"

VMRUN="$BIN_DIR/vmrun"
VMPREP="$BIN_DIR/vmprep_forth0"
MKIMAGE="$BIN_DIR/mkimage_std7_fixed"

TOK_FULLADDER="$BIN_DIR/mktok_test_fulladder"
TOK_ADD8="$BIN_DIR/mktok_test_add8"
TOK_EQ24="$BIN_DIR/mktok_test_eq24"
TOK_LT24="$BIN_DIR/mktok_test_lt24"
TOK_ADD24="$BIN_DIR/mktok_test_add24"
TOK_EQ24P="$BIN_DIR/mktok_test_eq24p"

SMALL_IMG="$OUT_DIR/img_fixed_pool_small.bin"
BIG_IMG="$OUT_DIR/img_fixed_pool_big.bin"

ONLY="${ONLY:-}"

mkdir -p "$OUT_DIR" "$TMP_DIR" "$FAIL_DIR"

command -v xxd >/dev/null 2>&1 || {
  echo "ERROR: xxd not found (needed by tests)" >&2
  exit 1
}

dump_vmrep () {
  f="$1"
  test -n "${COPYSPACE_REPORT:-}" || return 0
  if grep -q "^\[vmrep\]" "$f" 2>/dev/null; then
    echo "[vmrep] from $f" >&2
    sed -n '/^\[vmrep\]/,/VMREP_END/p' "$f" >&2
  fi
}

make_fail_bundle () {
  name="$1"
  reason="$2"
  ts="$(date +%Y%m%d_%H%M%S)"
  dir="$FAIL_DIR/${name}_${ts}"
  mkdir -p "$dir"

  echo "[FAIL-BUNDLE] $name: $reason" >&2
  echo "[FAIL-BUNDLE] dir=$dir" >&2

  for f in \
    "$TMP_DIR/tok.bin" "$TMP_DIR/compiled_space.bin" "$TMP_DIR/after.bin" \
    "$TMP_DIR/compile.log" "$TMP_DIR/run.log" "$TMP_DIR/prep.log" "$TMP_DIR/t.log" \
    "$TMP_DIR/got.bin" "$TMP_DIR/exp.bin"
  do
    if [ -f "$f" ]; then cp -a "$f" "$dir/"; fi
  done

  if [ -f "$SMALL_IMG" ]; then cp -a "$SMALL_IMG" "$dir/"; fi
  if [ -f "$BIG_IMG" ]; then cp -a "$BIG_IMG" "$dir/"; fi
}

run_case () {
  name="$1"
  tokgen="$2"
  exphex="$3"
  expn="$4"

  echo "" >&2
  echo "[test] $name" >&2

  rm -f "$TMP_DIR"/tok.bin "$TMP_DIR"/compiled_space.bin "$TMP_DIR"/after.bin \
        "$TMP_DIR"/compile.log "$TMP_DIR"/prep.log "$TMP_DIR"/run.log \
        "$TMP_DIR"/t.log "$TMP_DIR"/got.bin "$TMP_DIR"/exp.bin

  "$tokgen" --image "$SMALL_IMG" --out "$TMP_DIR/tok.bin" 2> "$TMP_DIR/t.log"
  B=$(sed -n 's/TESTG(byte)=\([0-9][0-9]*\).*/\1/p' "$TMP_DIR/t.log")
  test -n "$B"

  "$VMRUN" --image "$BIG_IMG" \
    --space-bytes "$SPACE_BYTES" --processor-n "$PROCESSOR_N" \
    --life "$LIFE_COMPILE" --dump "$TMP_DIR/compiled_space.bin" \
    < "$TMP_DIR/tok.bin" > /dev/null 2> "$TMP_DIR/compile.log" || {
      make_fail_bundle "$name" "compile vmrun failed"
      exit 1
    }

  grep -q "VM halted by MMIO.HALT" "$TMP_DIR/compile.log" || {
    make_fail_bundle "$name" "compile did not halt by MMIO.HALT"
    exit 1
  }
  dump_vmrep "$TMP_DIR/compile.log"

  "$VMPREP" --image "$TMP_DIR/compiled_space.bin" \
    --space-bytes "$SPACE_BYTES" --processor-n "$PROCESSOR_N" 2> "$TMP_DIR/prep.log" || {
      make_fail_bundle "$name" "vmprep failed"
      exit 1
    }

  "$VMRUN" --image "$TMP_DIR/compiled_space.bin" \
    --space-bytes "$SPACE_BYTES" --processor-n "$PROCESSOR_N" \
    --life "$LIFE_RUN" --dump "$TMP_DIR/after.bin" \
    < /dev/null > /dev/null 2> "$TMP_DIR/run.log" || {
      make_fail_bundle "$name" "run vmrun failed"
      exit 1
    }

  grep -q "VM halted by MMIO.HALT" "$TMP_DIR/run.log" || {
    make_fail_bundle "$name" "run did not halt by MMIO.HALT"
    exit 1
  }
  dump_vmrep "$TMP_DIR/run.log"

  dd if="$TMP_DIR/after.bin" bs=1 skip="$B" count="$expn" status=none > "$TMP_DIR/got.bin"
  echo "$exphex" | tr -d ' \n' | xxd -r -p > "$TMP_DIR/exp.bin"

  # TDD hook: force mismatch for fail-bundle test
  if [ -n "${FORCE_BAD_EXP:-}" ]; then
    printf '\xff' | dd of="$TMP_DIR/exp.bin" bs=1 seek=0 conv=notrunc status=none
  fi

  if ! cmp -s "$TMP_DIR/got.bin" "$TMP_DIR/exp.bin"; then
    echo "[FAIL] $name mismatch" >&2
    echo "got:" >&2; xxd -g 1 "$TMP_DIR/got.bin" >&2
    echo "exp:" >&2; xxd -g 1 "$TMP_DIR/exp.bin" >&2
    make_fail_bundle "$name" "mismatch"
    exit 1
  fi

  echo "[OK] $name" >&2
}

maybe_run () {
  name="$1"
  shift
  if [ -n "$ONLY" ] && [ "$ONLY" != "$name" ]; then
    return 0
  fi
  run_case "$name" "$@"
}

echo "[test] build images (small/big pool)" >&2
"$MKIMAGE" --out "$SMALL_IMG" --pool-cells "$POOL_SMALL" > /dev/null
"$MKIMAGE" --out "$BIG_IMG"   --pool-cells "$POOL_BIG"   > /dev/null

maybe_run "fulladder" "$TOK_FULLADDER" "00808040804040c0" 8
maybe_run "add8"      "$TOK_ADD8"      "00000000ff010080" 8
maybe_run "eq24"      "$TOK_EQ24"      "80008000" 4
maybe_run "eq24p"     "$TOK_EQ24P"     "80008000" 4
maybe_run "lt24"      "$TOK_LT24"      "008000800080" 6
maybe_run "add24"     "$TOK_ADD24" \
"00000000000000000000000000000000\
ffffff00000001000000000080000000\
12345600010203001336590000000000\
80000000800000000000000080000000" 64

echo "" >&2
echo "All tests passed." >&2
