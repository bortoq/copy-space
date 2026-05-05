#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_todoB_loadstore24p"
mkdir -p "$bakdir"

need_file() { [ -f "$1" ] || { echo "FAIL: missing $1" >&2; exit 1; }; }

backup() {
  f="$1"
  need_file "$f"
  cp -a "$f" "$bakdir/$(echo "$f" | tr '/ ' '__')"
}

# Ensure we run from project root (heuristic)
[ -d src ] && [ -d scripts ] || { echo "FAIL: run from project root (where src/ and scripts/ exist)" >&2; exit 1; }

F_ADDRS="src/mkimage/std7_fixed/addrs.h"
F_ARTH="src/mkimage/std7_fixed/artifacts.h"
F_ARTC="src/mkimage/std7_fixed/artifacts.c"
F_WALL="src/mkimage/std7_fixed/words_all.h"
F_LEG="src/mkimage/std7_fixed/legacy.c"
F_NEW="src/mkimage/std7_fixed/words_loadstore24p.c"

need_file "$F_ADDRS"
need_file "$F_ARTH"
need_file "$F_ARTC"
need_file "$F_WALL"
need_file "$F_LEG"

backup "$F_ADDRS"
backup "$F_ARTH"
backup "$F_ARTC"
backup "$F_WALL"
backup "$F_LEG"

tmpdir="tmp/apply_${ts}"
mkdir -p "$tmpdir"

# ---------- addrs.h: append fields after term0_desc ----------
if grep -q "word_load24ap" "$F_ADDRS"; then
  echo "SKIP: addrs.h already has word_load24* fields"
else
  ins="$tmpdir/addrs_ins.txt"
  cat >"$ins" <<'EOF'
  /* 2b block-pointer primitives (appended ABI): 67..69 */
  bitaddr_t word_load24ap;    /* ART[67] */
  bitaddr_t word_load24bp;    /* ART[68] */
  bitaddr_t word_store24rp;   /* ART[69] */
EOF
  out="$tmpdir/addrs.h"
  # insert after the term0_desc line
  sed '/bitaddr_t term0_desc;[[:space:]]*\/\* ART\[66\] \*\//r '"$ins"'' "$F_ADDRS" >"$out" \
    || { echo "FAIL: cannot patch addrs.h (anchor term0_desc ART[66])" >&2; exit 1; }
  mv "$out" "$F_ADDRS"
  echo "OK: patched addrs.h"
fi

# ---------- artifacts.h: insert new enum entries + bump ART_COUNT ----------
if grep -q "ART_WORD_LOAD24AP" "$F_ARTH"; then
  echo "SKIP: artifacts.h already has ART_WORD_LOAD24*"
else
  ins="$tmpdir/arth_ins.txt"
  cat >"$ins" <<'EOF'

  /* 2b block-pointer primitives (appended ABI) */
  ART_WORD_LOAD24AP  = 67,
  ART_WORD_LOAD24BP  = 68,
  ART_WORD_STORE24RP = 69,
EOF
  out="$tmpdir/artifacts.h.1"
  sed '/ART_TERM0_DESC[[:space:]]*=[[:space:]]*66[[:space:]]*,/r '"$ins"'' "$F_ARTH" >"$out" \
    || { echo "FAIL: cannot patch artifacts.h (anchor ART_TERM0_DESC=66)" >&2; exit 1; }

  out2="$tmpdir/artifacts.h.2"
  # bump ART_COUNT (only if it still says 67; otherwise set to 70 anyway)
  sed 's/ART_COUNT[[:space:]]*=[[:space:]]*[0-9][0-9]*/ART_COUNT = 70/' "$out" >"$out2"
  mv "$out2" "$F_ARTH"
  echo "OK: patched artifacts.h"
fi

# ---------- artifacts.c: append writes for bus + new words ----------
# (also fixes missing bus writes in the file you showed)
if grep -q "ART_WORD_STORE24RP" "$F_ARTC"; then
  echo "SKIP: artifacts.c already writes ART_WORD_STORE24RP"
else
  ins="$tmpdir/artc_ins.txt"
  cat >"$ins" <<'EOF'

  /* device/bus */
  artw(vm, ART, ART_BUS_BASE,   A->bus_base);
  artw(vm, ART, ART_TERM0_DESC, A->term0_desc);

  /* 2b block-pointer primitives */
  artw(vm, ART, ART_WORD_LOAD24AP,  A->word_load24ap);
  artw(vm, ART, ART_WORD_LOAD24BP,  A->word_load24bp);
  artw(vm, ART, ART_WORD_STORE24RP, A->word_store24rp);
EOF
  out="$tmpdir/artifacts.c"
  sed '/artw(vm, ART, ART_TESTSCR_END[[:space:]]*,[[:space:]]*A->testscr_end);/r '"$ins"'' "$F_ARTC" >"$out" \
    || { echo "FAIL: cannot patch artifacts.c (anchor ART_TESTSCR_END write)" >&2; exit 1; }
  mv "$out" "$F_ARTC"
  echo "OK: patched artifacts.c"
fi

# ---------- words_all.h: add prototypes before write_cell ----------
if grep -q "write_word_load24ap" "$F_WALL"; then
  echo "SKIP: words_all.h already has load/store prototypes"
else
  ins="$tmpdir/words_all_ins.txt"
  cat >"$ins" <<'EOF'

/* todo B: 2b block-pointer primitives */
void write_word_load24ap(vm_t *vm,
                         bitaddr_t img, bitaddr_t next_img,
                         bitaddr_t var_ap,
                         bitaddr_t var_a24);
void write_word_load24bp(vm_t *vm,
                         bitaddr_t img, bitaddr_t next_img,
                         bitaddr_t var_bp,
                         bitaddr_t var_b24);
void write_word_store24rp(vm_t *vm,
                          bitaddr_t img, bitaddr_t next_img,
                          bitaddr_t var_rp,
                          bitaddr_t var_sum24);
EOF
  out="$tmpdir/words_all.h"
  awk -v INSFILE="$ins" '
    BEGIN { inserted=0 }
    /^void write_cell\(vm_t \*vm/ {
      if (!inserted) {
        while ((getline line < INSFILE) > 0) print line;
        close(INSFILE);
        inserted=1;
      }
    }
    { print }
    END { if (!inserted) exit 2 }
  ' "$F_WALL" >"$out" || { echo "FAIL: cannot patch words_all.h (anchor write_cell)" >&2; exit 1; }
  mv "$out" "$F_WALL"
  echo "OK: patched words_all.h"
fi

# ---------- legacy.c: add word addresses 26..28 ----------
if grep -q "WORD_LOAD24AP" "$F_LEG"; then
  echo "SKIP: legacy.c already defines WORD_LOAD24AP"
else
  ins="$tmpdir/legacy_addr_ins.txt"
  cat >"$ins" <<'EOF'

  // NEW: block-pointer primitives (todo B)
  bitaddr_t WORD_LOAD24AP  = WORDS_BASE + 26*STEP;
  bitaddr_t WORD_LOAD24BP  = WORDS_BASE + 27*STEP;
  bitaddr_t WORD_STORE24RP = WORDS_BASE + 28*STEP;
EOF
  out="$tmpdir/legacy.c.1"
  sed '/bitaddr_t WORD_LITRP[[:space:]]*=[[:space:]]*WORDS_BASE[[:space:]]*+[[:space:]]*25\*STEP;/r '"$ins"'' "$F_LEG" >"$out" \
    || { echo "FAIL: cannot patch legacy.c (anchor WORD_LITRP definition)" >&2; exit 1; }
  mv "$out" "$F_LEG"
  echo "OK: patched legacy.c (word addresses)"
fi

# ---------- legacy.c: add builder calls ----------
if grep -q "write_word_store24rp" "$F_LEG"; then
  echo "SKIP: legacy.c already calls write_word_store24rp"
else
  ins="$tmpdir/legacy_call_ins.txt"
  cat >"$ins" <<'EOF'

  // NEW block-pointer primitives (todo B)
  write_word_load24ap(&vm, WORD_LOAD24AP, NEXT_IMG, VAR_AP, VAR_A24);
  write_word_load24bp(&vm, WORD_LOAD24BP, NEXT_IMG, VAR_BP, VAR_B24);
  write_word_store24rp(&vm, WORD_STORE24RP, NEXT_IMG, VAR_RP, VAR_SUM24);
EOF
  out="$tmpdir/legacy.c.2"
  sed '/write_word_lit_generic(&vm, WORD_LITRP,/r '"$ins"'' "$F_LEG" >"$out" \
    || { echo "FAIL: cannot patch legacy.c (anchor write_word_lit_generic WORD_LITRP)" >&2; exit 1; }
  mv "$out" "$F_LEG"
  echo "OK: patched legacy.c (builder calls)"
fi

# ---------- legacy.c: add A.* assignments ----------
if grep -q "A.word_load24ap" "$F_LEG"; then
  echo "SKIP: legacy.c already assigns A.word_load24ap"
else
  ins="$tmpdir/legacy_A_ins.txt"
  cat >"$ins" <<'EOF'
  A.word_load24ap  = WORD_LOAD24AP;
  A.word_load24bp  = WORD_LOAD24BP;
  A.word_store24rp = WORD_STORE24RP;
EOF
  out="$tmpdir/legacy.c.3"
  sed '/A.word_litrp[[:space:]]*=[[:space:]]*WORD_LITRP;/r '"$ins"'' "$F_LEG" >"$out" \
    || { echo "FAIL: cannot patch legacy.c (anchor A.word_litrp assignment)" >&2; exit 1; }
  mv "$out" "$F_LEG"
  echo "OK: patched legacy.c (A assignments)"
fi

# ---------- new C module ----------
if [ -f "$F_NEW" ]; then
  echo "SKIP: $F_NEW already exists"
else
  cat >"$F_NEW" <<'EOF'
/* file: src/mkimage/std7_fixed/words_loadstore24p.c
 * date: 2026-05-05
 * purpose: todo B: 2b block-pointer primitives (LOAD24AP/LOAD24BP/STORE24RP)
 */
#include "words.h"
#include "words_int.h"
#include <stdint.h>

static void fill_to_last_slot(vm_t *vm, bitaddr_t img, unsigned s) {
  unsigned last_slot = vm->processor_n - 1;
  while (s < last_slot) {
    vm_write_inst(vm, img + (bitaddr_t)s*(bitaddr_t)vm->instr_bits, (vm_inst_t){0,0,0});
    s++;
  }
}

void write_word_load24ap(vm_t *vm,
                         bitaddr_t img, bitaddr_t chain_next,
                         bitaddr_t var_ap,
                         bitaddr_t var_a24)
{
  nop_fill_image(vm, img);
  const unsigned A = vm->addr_bits;

  unsigned s = 0;
  unsigned S_PATCH = s++;
  unsigned S_READ  = s++;

  vm_write_inst(vm, img + (bitaddr_t)S_READ*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=24, .dst=(uint64_t)var_a24, .src=0 });

  bitaddr_t read_src_field = vm_proc_slot_field_ip(vm, S_READ, vm->off_src);
  vm_write_inst(vm, img + (bitaddr_t)S_PATCH*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=(uint64_t)read_src_field, .src=(uint64_t)var_ap });

  fill_to_last_slot(vm, img, s);
  write_chain_load(vm, img, chain_next);
}

void write_word_load24bp(vm_t *vm,
                         bitaddr_t img, bitaddr_t chain_next,
                         bitaddr_t var_bp,
                         bitaddr_t var_b24)
{
  nop_fill_image(vm, img);
  const unsigned A = vm->addr_bits;

  unsigned s = 0;
  unsigned S_PATCH = s++;
  unsigned S_READ  = s++;

  vm_write_inst(vm, img + (bitaddr_t)S_READ*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=24, .dst=(uint64_t)var_b24, .src=0 });

  bitaddr_t read_src_field = vm_proc_slot_field_ip(vm, S_READ, vm->off_src);
  vm_write_inst(vm, img + (bitaddr_t)S_PATCH*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=(uint64_t)read_src_field, .src=(uint64_t)var_bp });

  fill_to_last_slot(vm, img, s);
  write_chain_load(vm, img, chain_next);
}

void write_word_store24rp(vm_t *vm,
                          bitaddr_t img, bitaddr_t chain_next,
                          bitaddr_t var_rp,
                          bitaddr_t var_sum24)
{
  nop_fill_image(vm, img);
  const unsigned A = vm->addr_bits;

  unsigned s = 0;
  unsigned S_PATCH = s++;
  unsigned S_WRITE = s++;

  vm_write_inst(vm, img + (bitaddr_t)S_WRITE*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=24, .dst=0, .src=(uint64_t)var_sum24 });

  bitaddr_t write_dst_field = vm_proc_slot_field_ip(vm, S_WRITE, vm->off_dst);
  vm_write_inst(vm, img + (bitaddr_t)S_PATCH*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=(uint64_t)write_dst_field, .src=(uint64_t)var_rp });

  fill_to_last_slot(vm, img, s);
  write_chain_load(vm, img, chain_next);
}
EOF
  echo "OK: created $F_NEW"
fi

echo "DONE: backups in $bakdir"
echo "Next: run: make test"
