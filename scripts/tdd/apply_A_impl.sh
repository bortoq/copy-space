#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"

backup() {
  f="$1"
  test -f "$f"
  cp -a "$f" "$f.bak.$ts"
  echo "[apply] backup $f -> $f.bak.$ts" >&2
}

patch_space_h() {
  f="src/vm/space.h"
  backup "$f"

  python3 - "$f" <<'PY'
import sys, re
from pathlib import Path

path = Path(sys.argv[1])
s = path.read_text(encoding="utf-8", errors="replace")

if "VM_E_SRC_BOUNDS" in s and "last_err" in s:
    print("[apply] space.h: already patched")
    sys.exit(0)

# Insert error types before vm_rc_t enum
m = re.search(r'\ntypedef\s+enum\s*\{\s*\n\s*VM_OK', s)
if not m:
    raise SystemExit("space.h: cannot find vm_rc_t enum to insert before")

ins = r'''
/* -------------------- VM error diagnostics (recorded on VM_ERR) -------------------- */

typedef enum {
  VM_E_NONE = 0,
  VM_E_SRC_BOUNDS = 1,
  VM_E_DST_BOUNDS = 2
} vm_err_kind_t;

typedef struct {
  vm_err_kind_t kind;
  uint64_t tick;     /* 0-based tick index */
  unsigned slot;     /* processor slot index */
  vm_inst_t ins;     /* offending instruction */
  bitaddr_t space_bits;
} vm_err_t;

'''
s = s[:m.start()] + "\n" + ins + s[m.start():]

# Add fields into vm_t before closing brace
m2 = re.search(r'\n\} vm_t;\n', s)
if not m2:
    raise SystemExit("space.h: cannot find end of vm_t")

# Find start of vm_t to insert before its end, but after workspace_base.
# We'll insert near the end unconditionally.
insert = r'''
  /* diagnostics */
  uint64_t tick_counter; /* increments per vm_tick() call that completes */
  vm_err_t last_err;
'''
# Insert before "} vm_t;"
s = s[:m2.start()] + insert + s[m2.start():]

path.write_text(s, encoding="utf-8")
print("[apply] space.h: patched")
PY
}

patch_space_c() {
  f="src/vm/space.c"
  backup "$f"

  python3 - "$f" <<'PY'
import sys, re
from pathlib import Path

path = Path(sys.argv[1])
s = path.read_text(encoding="utf-8", errors="replace")

# Ensure we patch vm_tick bounds checks and set last_err.
if "VM_E_SRC_BOUNDS" in s and "vm->last_err" in s and "tick_counter" in s:
    print("[apply] space.c: looks already patched (found VM_E_SRC_BOUNDS + tick_counter)")
    sys.exit(0)

# Patch bounds checks inside vm_tick:
# Replace:
#   if (src + n > vm->space_bits) return VM_ERR;
#   if (dst + n > vm->space_bits) return VM_ERR;
#
# with recording last_err.
pat = r'''
(\s*)if\s*\(\s*src\s*\+\s*n\s*>\s*vm->space_bits\s*\)\s*return\s+VM_ERR\s*;
\s*
\1if\s*\(\s*dst\s*\+\s*n\s*>\s*vm->space_bits\s*\)\s*return\s+VM_ERR\s*;
'''

repl = r'''
\1if (src + n > vm->space_bits) {
\1  vm->last_err.kind = VM_E_SRC_BOUNDS;
\1  vm->last_err.tick = vm->tick_counter;
\1  vm->last_err.slot = i;
\1  vm->last_err.ins  = ins;
\1  vm->last_err.space_bits = vm->space_bits;
\1  return VM_ERR;
\1}
\1if (dst + n > vm->space_bits) {
\1  vm->last_err.kind = VM_E_DST_BOUNDS;
\1  vm->last_err.tick = vm->tick_counter;
\1  vm->last_err.slot = i;
\1  vm->last_err.ins  = ins;
\1  vm->last_err.space_bits = vm->space_bits;
\1  return VM_ERR;
\1}
'''

s2 = re.sub(pat, repl, s, flags=re.M)
if s2 == s:
    raise SystemExit("space.c: failed to replace bounds checks (pattern not found)")
s = s2

# Initialize last_err at start of vm_tick (just after null checks)
# Find line: if (!vm || !vm->space) return VM_ERR;
m = re.search(r'vm_rc_t\s+vm_tick[^{]*\{\s*\n\s*if\s*\(!vm\s*\|\|\s*!vm->space\)\s*return\s+VM_ERR\s*;\s*\n', s)
if not m:
    raise SystemExit("space.c: cannot find vm_tick prologue for inserting last_err init")

ins = r'''  /* diagnostics: reset last_err for this tick */
  vm->last_err.kind = VM_E_NONE;
  vm->last_err.tick = vm->tick_counter;
  vm->last_err.slot = 0;
  vm->last_err.ins  = (vm_inst_t){0,0,0};
  vm->last_err.space_bits = vm->space_bits;

'''
s = s[:m.end()] + ins + s[m.end():]

# Increment tick_counter on normal OK path (before return VM_OK),
# and also on HALT path (before return VM_HALT), so tick_counter is meaningful.
# HALT return:
s2 = re.sub(r'(\s*)if\s*\(vm_bit_get\(vm,\s*vm->mmio\.halt\)\)\s*return\s+VM_HALT\s*;',
            r'\1if (vm_bit_get(vm, vm->mmio.halt)) { vm->tick_counter++; return VM_HALT; }',
            s, count=1)
s = s2

# OK return:
s2 = re.sub(r'(\s*)return\s+VM_OK\s*;',
            r'\1vm->tick_counter++;\n\1return VM_OK;',
            s, count=1)
if s2 == s:
    raise SystemExit("space.c: cannot find return VM_OK to patch tick_counter++")
s = s2

path.write_text(s, encoding="utf-8")
print("[apply] space.c: patched")
PY
}

patch_vmrun_c() {
  f="src/tools/vmrun.c"
  if [ ! -f "$f" ]; then
    echo "[apply] vmrun.c not found at $f (skip)" >&2
    return 0
  fi
  backup "$f"

  python3 - "$f" <<'PY'
import sys, re
from pathlib import Path

path = Path(sys.argv[1])
s = path.read_text(encoding="utf-8", errors="replace")

if "VM_ERR:" in s and "tick=" in s and "slot=" in s:
    print("[apply] vmrun.c: already patched")
    sys.exit(0)

# Ensure <inttypes.h> included (for PRIu64)
if "<inttypes.h>" not in s:
    # insert after std headers if possible
    s = re.sub(r'(#include\s+<stdint\.h>\s*\n)', r'\1#include <inttypes.h>\n', s, count=1)

# We need to find where rc is handled and VM_ERR printed.
# We'll patch by inserting a block that, when rc==VM_ERR, prints diagnostics from vm->last_err.
# Search for "if (rc == VM_ERR" or "case VM_ERR".
m = re.search(r'if\s*\(\s*rc\s*==\s*VM_ERR\s*\)\s*\{', s)
if m:
    # Insert inside this block early
    open_brace = m.end()-1
    ins = r'''
    /* VM error diagnostics */
    fprintf(stderr,
            "VM_ERR: tick=%" PRIu64 " slot=%u n=%" PRIu64 " dst=%" PRIu64 " src=%" PRIu64 " kind=%d space_bits=%" PRIu64 "\n",
            (uint64_t)vm.last_err.tick,
            (unsigned)vm.last_err.slot,
            (uint64_t)vm.last_err.ins.n,
            (uint64_t)vm.last_err.ins.dst,
            (uint64_t)vm.last_err.ins.src,
            (int)vm.last_err.kind,
            (uint64_t)vm.last_err.space_bits);
'''
    s = s[:open_brace+1] + ins + s[open_brace+1:]
    path.write_text(s, encoding="utf-8")
    print("[apply] vmrun.c: patched inside existing (rc==VM_ERR) block")
    sys.exit(0)

# Fallback: patch switch(rc) { case VM_ERR: ... }
m = re.search(r'case\s+VM_ERR\s*:\s*', s)
if m:
    ins = r'''
      fprintf(stderr,
              "VM_ERR: tick=%" PRIu64 " slot=%u n=%" PRIu64 " dst=%" PRIu64 " src=%" PRIu64 " kind=%d space_bits=%" PRIu64 "\n",
              (uint64_t)vm.last_err.tick,
              (unsigned)vm.last_err.slot,
              (uint64_t)vm.last_err.ins.n,
              (uint64_t)vm.last_err.ins.dst,
              (uint64_t)vm.last_err.ins.src,
              (int)vm.last_err.kind,
              (uint64_t)vm.last_err.space_bits);
'''
    s = s[:m.end()] + ins + s[m.end():]
    path.write_text(s, encoding="utf-8")
    print("[apply] vmrun.c: patched inside switch-case VM_ERR")
    sys.exit(0)

raise SystemExit("vmrun.c: cannot find rc==VM_ERR block or case VM_ERR to patch; paste vmrun.c and I'll provide exact diff")
PY
}

patch_mkimage_c() {
  f="src/mkimage/mkimage_std7_fixed.c"
  if [ ! -f "$f" ]; then
    echo "[apply] mkimage_std7_fixed.c not found at $f (skip)" >&2
    return 0
  fi
  backup "$f"

  python3 - "$f" <<'PY'
import sys, re
from pathlib import Path

path = Path(sys.argv[1])
s = path.read_text(encoding="utf-8", errors="replace")

if "TESTSCR_BASE(byte)=" in s and "TESTSCR_SIZE(byte)=" in s:
    print("[apply] mkimage: already patched")
    sys.exit(0)

# We inject printing near existing summary print (WORDS_BASE/STEP/OFFTAB are already printed in your output).
# We'll look for "WORDS_BASE(byte)=" print and insert two more prints after it.
m = re.search(r'(WORDS_BASE\(byte\)=.*\n)', s)
if not m:
    raise SystemExit("mkimage: cannot find 'WORDS_BASE(byte)=' print site to insert TESTSCR prints")

ins = r'''  /* standardized test scratch region (bytes) */
  /* by convention: place it just before WORDS_BASE; keep it fixed across POOL_CELLS */
  size_t testscr_size = 8192;
  size_t testscr_base = (WORDS_BASE >= testscr_size) ? (WORDS_BASE - testscr_size) : 0;
  printf("  TESTSCR_BASE(byte)=%zu\n", testscr_base);
  printf("  TESTSCR_SIZE(byte)=%zu\n", testscr_size);
'''
# Insert after the matched WORDS_BASE print line. This relies on local variable WORDS_BASE in mkimage file.
s = s[:m.end()] + ins + s[m.end():]

path.write_text(s, encoding="utf-8")
print("[apply] mkimage: inserted TESTSCR_BASE/SIZE prints (base=WORDS_BASE-8192)")
PY
}

install_test_all_sh() {
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

  # copy what exists
  for f in \
    "$TMP_DIR/tok.bin" "$TMP_DIR/compiled_space.bin" "$TMP_DIR/after.bin" \
    "$TMP_DIR/compile.log" "$TMP_DIR/run.log" "$TMP_DIR/prep.log" "$TMP_DIR/t.log" \
    "$TMP_DIR/got.bin" "$TMP_DIR/exp.bin"
  do
    if [ -f "$f" ]; then cp -a "$f" "$dir/"; fi
  done

  # also store images (helpful for repro)
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

  # TDD hook: force mismatch
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
  echo "[apply] installed scripts/test_all.sh with fail-bundles + FORCE_BAD_EXP" >&2
}

patch_space_h
patch_space_c
patch_vmrun_c
patch_mkimage_c
install_test_all_sh

echo "[apply] done. rebuild and rerun TDD:" >&2
echo "  make clean && make" >&2
echo "  scripts/tdd/run_all.sh" >&2