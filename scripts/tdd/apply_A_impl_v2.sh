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

if "typedef enum {\n  VM_E_NONE" in s and "vm_err_t last_err" in s:
    print("[apply] space.h: already patched")
    sys.exit(0)

# Insert vm_err_kind_t/vm_err_t after vm_inst_t (right after its typedef)
m = re.search(r'typedef\s+struct\s*\{\s*\n\s*uint64_t\s+n;\s*\n\s*uint64_t\s+dst;\s*\n\s*uint64_t\s+src;\s*\n\s*\}\s*vm_inst_t;\s*\n', s)
if not m:
    raise SystemExit("space.h: cannot find vm_inst_t typedef block")

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
s = s[:m.end()] + ins + s[m.end():]

# Add fields to vm_t near end (before "} vm_t;")
m2 = re.search(r'\n\}\s*vm_t;\s*\n', s)
if not m2:
    raise SystemExit("space.h: cannot find end of vm_t")

insert = r'''
  /* diagnostics */
  uint64_t tick_counter; /* increments per vm_tick() that completes (OK or HALT) */
  vm_err_t last_err;
'''
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

if "VM_E_SRC_BOUNDS" in s and "VM_ERR: tick=" in s and "tick_counter" in s:
    print("[apply] space.c: already patched for VM_ERR diag")
    sys.exit(0)

# 1) Insert last_err reset block after: if (!vm || !vm->space) return VM_ERR;
needle = "  if (!vm || !vm->space) return VM_ERR;\n"
pos = s.find(needle)
if pos < 0:
    raise SystemExit("space.c: cannot find vm_tick prologue null-check line")

ins = r'''
  /* diagnostics: reset last_err for this tick */
  vm->last_err.kind = VM_E_NONE;
  vm->last_err.tick = vm->tick_counter;
  vm->last_err.slot = 0;
  vm->last_err.ins  = (vm_inst_t){0,0,0};
  vm->last_err.space_bits = vm->space_bits;

'''
s = s[:pos+len(needle)] + ins + s[pos+len(needle):]

# 2) Patch HALT return to increment tick_counter
s2 = s.replace(
    "  if (vm_bit_get(vm, vm->mmio.halt)) return VM_HALT;\n",
    "  if (vm_bit_get(vm, vm->mmio.halt)) { vm->tick_counter++; return VM_HALT; }\n",
    1
)
if s2 == s:
    raise SystemExit("space.c: cannot patch HALT return (line not found as expected)")
s = s2

# 3) Replace src bounds check line with recording + fprintf + return
src_line = "    if (src + n > vm->space_bits) return VM_ERR;\n"
if src_line not in s:
    raise SystemExit("space.c: src bounds check line not found (expected exact line)")
src_block = r'''    if (src + n > vm->space_bits) {
      vm->last_err.kind = VM_E_SRC_BOUNDS;
      vm->last_err.tick = vm->tick_counter;
      vm->last_err.slot = i;
      vm->last_err.ins  = ins;
      vm->last_err.space_bits = vm->space_bits;
      fprintf(stderr,
              "VM_ERR: tick=%" PRIu64 " slot=%u n=%" PRIu64 " dst=%" PRIu64 " src=%" PRIu64 " kind=%d space_bits=%" PRIu64 "\n",
              (uint64_t)vm->last_err.tick,
              (unsigned)vm->last_err.slot,
              (uint64_t)vm->last_err.ins.n,
              (uint64_t)vm->last_err.ins.dst,
              (uint64_t)vm->last_err.ins.src,
              (int)vm->last_err.kind,
              (uint64_t)vm->last_err.space_bits);
      return VM_ERR;
    }
'''
s = s.replace(src_line, src_block, 1)

# 4) Replace dst bounds check line similarly
dst_line = "    if (dst + n > vm->space_bits) return VM_ERR;\n"
if dst_line not in s:
    raise SystemExit("space.c: dst bounds check line not found (expected exact line)")
dst_block = r'''    if (dst + n > vm->space_bits) {
      vm->last_err.kind = VM_E_DST_BOUNDS;
      vm->last_err.tick = vm->tick_counter;
      vm->last_err.slot = i;
      vm->last_err.ins  = ins;
      vm->last_err.space_bits = vm->space_bits;
      fprintf(stderr,
              "VM_ERR: tick=%" PRIu64 " slot=%u n=%" PRIu64 " dst=%" PRIu64 " src=%" PRIu64 " kind=%d space_bits=%" PRIu64 "\n",
              (uint64_t)vm->last_err.tick,
              (unsigned)vm->last_err.slot,
              (uint64_t)vm->last_err.ins.n,
              (uint64_t)vm->last_err.ins.dst,
              (uint64_t)vm->last_err.ins.src,
              (int)vm->last_err.kind,
              (uint64_t)vm->last_err.space_bits);
      return VM_ERR;
    }
'''
s = s.replace(dst_line, dst_block, 1)

# 5) Insert tick_counter++ before return VM_OK; (must be after vmrep_tick_end if present)
# We patch the final "return VM_OK;" inside vm_tick (first occurrence after vmrep_tick_end).
m = re.search(r'\n\s*vmrep_tick_end\(\);\s*\n\s*\n\s*return\s+VM_OK;\s*\n\}', s)
if not m:
    # fallback: patch first "return VM_OK;" inside vm_tick by anchor "vmrep_tick_end();"
    anchor = "  vmrep_tick_end();\n\n\n  return VM_OK;\n"
    if anchor not in s:
        raise SystemExit("space.c: cannot find vmrep_tick_end()+return VM_OK block to insert tick_counter++")
    s = s.replace(anchor, "  vmrep_tick_end();\n\n  vm->tick_counter++;\n\n  return VM_OK;\n", 1)
else:
    # do a simple replace in that matched region
    s = s.replace("  return VM_OK;\n", "  vm->tick_counter++;\n\n  return VM_OK;\n", 1)

path.write_text(s, encoding="utf-8")
print("[apply] space.c: patched VM_ERR diagnostics + tick_counter")
PY
}

patch_mkimage() {
  f="src/mkimage/mkimage_std7_fixed.c"
  if [ ! -f "$f" ]; then
    echo "[apply] mkimage file not found: $f (skip)" >&2
    return 0
  fi
  backup "$f"

  python3 - "$f" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
s = path.read_text(encoding="utf-8", errors="replace")

if "TESTSCR_BASE(byte)=" in s and "TESTSCR_SIZE(byte)=" in s:
    print("[apply] mkimage: already has TESTSCR prints")
    sys.exit(0)

# Very safe patch: after the first occurrence of the format literal "WORDS_BASE(byte)="
# insert two additional printf lines that do not reference local variables.
key = "WORDS_BASE(byte)="
idx = s.find(key)
if idx < 0:
    raise SystemExit("mkimage: cannot find 'WORDS_BASE(byte)=' literal in source")

# find the semicolon of the printf that contains WORDS_BASE(byte)=
semi = s.find(";", idx)
if semi < 0:
    raise SystemExit("mkimage: cannot find ';' after WORDS_BASE print")

ins = '\n  printf("  TESTSCR_BASE(byte)=%u\\n", 0u);\n  printf("  TESTSCR_SIZE(byte)=%u\\n", 8192u);\n'
s = s[:semi+1] + ins + s[semi+1:]

path.write_text(s, encoding="utf-8")
print("[apply] mkimage: inserted TESTSCR_BASE/SIZE prints (temporary base=0, size=8192)")
PY
}

install_test_all() {
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

patch_space_h
patch_space_c
patch_mkimage
install_test_all

echo "[apply] done. Now rebuild + run TDD:" >&2
echo "  make clean && make" >&2
echo "  scripts/tdd/run_all.sh" >&2