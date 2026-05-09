#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"

backup() {
  f="$1"
  test -f "$f"
  cp -a "$f" "$f.bak.$ts"
  echo "[apply] backup $f -> $f.bak.$ts" >&2
}

patch_vmrun_exitcode() {
  f="src/tools/vmrun.c"
  if [ ! -f "$f" ]; then
    echo "[apply] vmrun.c not found at $f; cannot patch exit code. Paste vmrun.c and I'll provide exact diff." >&2
    exit 2
  fi
  backup "$f"

  python3 - "$f" <<'PY'
import sys, re
from pathlib import Path

path = Path(sys.argv[1])
s = path.read_text(encoding="utf-8", errors="replace")

# If already returns nonzero on VM_ERR (heuristic), skip
if re.search(r'VM_ERR[\s\S]{0,200}return\s+1\s*;', s) or re.search(r'VM error[\s\S]{0,200}return\s+1\s*;', s):
    print("[apply] vmrun.c: looks already returning 1 on VM_ERR (skip)")
    sys.exit(0)

# Strategy 1: find a block that prints "VM error" and returns 0; change to return 1
s2, n = re.subn(r'(VM error[^\n]*\n[^\n]*\n)(\s*return\s+)0(\s*;)', r'\g<1>\g<2>1\g<3>', s, count=1)
if n == 1:
    path.write_text(s2, encoding="utf-8")
    print("[apply] vmrun.c: patched return 0->1 after 'VM error' print")
    sys.exit(0)

# Strategy 2: if (rc == VM_ERR) { ... return 0; }  => return 1;
m = re.search(r'if\s*\(\s*rc\s*==\s*VM_ERR\s*\)\s*\{', s)
if m:
    # replace first 'return 0;' after that point within 400 chars
    head = s[:m.end()]
    tail = s[m.end():]
    tail2, n2 = re.subn(r'return\s+0\s*;', 'return 1;', tail, count=1)
    if n2 == 1:
        path.write_text(head + tail2, encoding="utf-8")
        print("[apply] vmrun.c: patched return inside if(rc==VM_ERR)")
        sys.exit(0)

# Strategy 3: switch(rc) case VM_ERR: ... return 0;
m = re.search(r'case\s+VM_ERR\s*:', s)
if m:
    head = s[:m.end()]
    tail = s[m.end():]
    tail2, n3 = re.subn(r'return\s+0\s*;', 'return 1;', tail, count=1)
    if n3 == 1:
        path.write_text(head + tail2, encoding="utf-8")
        print("[apply] vmrun.c: patched return inside case VM_ERR")
        sys.exit(0)

raise SystemExit("vmrun.c: could not find where VM_ERR returns 0. Paste vmrun.c and I'll patch precisely.")
PY
}

patch_mkimage_testscr_prints() {
  f="src/mkimage/mkimage_std7_fixed.c"
  if [ ! -f "$f" ]; then
    echo "[apply] mkimage_std7_fixed.c not found at $f; cannot patch TESTSCR prints." >&2
    exit 2
  fi
  backup "$f"

  python3 - "$f" <<'PY'
import sys, re
from pathlib import Path

path = Path(sys.argv[1])
s = path.read_text(encoding="utf-8", errors="replace")

if "TESTSCR_BASE(byte)=" in s and "TESTSCR_SIZE(byte)=" in s:
    print("[apply] mkimage: TESTSCR prints already present (skip)")
    sys.exit(0)

# Find the printf that prints WORDS_BASE(byte)=... and insert two prints after it.
# In your runtime output it prints exactly: "  WORDS_BASE(byte)=... STEP(bytes)=..."
pat = r'(printf\(\s*"\s*  WORDS_BASE\(byte\)=.*?;\s*\n)'
m = re.search(pat, s, flags=re.S)
if not m:
    raise SystemExit("mkimage: could not locate printf(\"  WORDS_BASE(byte)=..."); paste that region and I'll patch.")

ins = r'''  printf("  TESTSCR_BASE(byte)=%u\n", 0u);
  printf("  TESTSCR_SIZE(byte)=%u\n", 8192u);
'''
s = s[:m.end()] + ins + s[m.end():]

path.write_text(s, encoding="utf-8")
print("[apply] mkimage: inserted TESTSCR_* prints (temporary base=0, size=8192)")
PY
}

install_test_all_with_failbundles() {
  f="scripts/test_all.sh"
  backup "$f"

  cat > "$f" <<'SH'
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
SH

  chmod +x "$f"
  echo "[apply] installed scripts/test_all.sh with fail bundles + FORCE_BAD_EXP" >&2
}

patch_vmrun_exitcode
patch_mkimage_testscr_prints
install_test_all_with_failbundles

echo "[apply] done. Now rebuild + rerun TDD:" >&2
echo "  make clean && make" >&2
echo "  scripts/tdd/run_all.sh" >&2
