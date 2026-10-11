/* main.inc — forth0c entrypoint TU (included by src/tools/forth0c.c). */

#define _GNU_SOURCE
#include "space.h"
#include "mkimage/std7_fixed/artifacts.h"

#include <ctype.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* const table */
typedef struct { char *name; uint64_t val; } const_ent_t;
typedef struct { const_ent_t *v; size_t n, cap; } consttab_t;

static void *xrealloc(void *p, size_t n) {
  void *q = realloc(p, n);
  if (!q) { fprintf(stderr, "forth0c: OOM\n"); exit(1); }
  return q;
}
static char *xstrdup(const char *s) {
  size_t n = strlen(s);
  char *p = (char*)malloc(n + 1u);
  if (!p) { fprintf(stderr, "forth0c: OOM\n"); exit(1); }
  memcpy(p, s, n + 1u);
  return p;
}
static void const_set(consttab_t *ct, const char *name, uint64_t val) {
  for (size_t i = 0; i < ct->n; i++) {
    if (strcmp(ct->v[i].name, name) == 0) { ct->v[i].val = val; return; }
  }
  if (ct->n == ct->cap) {
    size_t nc = ct->cap ? ct->cap * 2u : 16u;
    ct->v = (const_ent_t*)xrealloc(ct->v, nc * sizeof(ct->v[0]));
    ct->cap = nc;
  }
  ct->v[ct->n].name = xstrdup(name);
  ct->v[ct->n].val = val;
  ct->n++;
}
static int const_get(consttab_t *ct, const char *name, uint64_t *out) {
  for (size_t i = 0; i < ct->n; i++) {
    if (strcmp(ct->v[i].name, name) == 0) { *out = ct->v[i].val; return 1; }
  }
  return 0;
}

/* symbols + lexer */
#include "syms.inc"
#include "lex.inc"

/* macros */
#include "macros.inc"

/* parser state */
typedef struct {
  lex_t *lx;
  int have;
  token_t cur;
  vm_t *vm;
  bitaddr_t ART;
  unsigned art_count;
  consttab_t consts;
  macrotab_t macros;

  /* page definition state */
  bitaddr_t page_addr;   /* current page bitaddr, 0 if not in page */
  unsigned  page_slot;   /* next slot index within page */

  /* conditional compilation stack */
#define IF_STACK_MAX 64
  int   if_stack[IF_STACK_MAX]; /* 1=compiling, 0=skipping */
  int   if_depth;               /* current nesting depth, -1 = no if */

  /* toggles */
  unsigned flags;        /* bitmask of enabled toggles */
} pstate_t;

static token_t p_peek(pstate_t *ps) {
  if (!ps->have) { ps->cur = lex_next(ps->lx); ps->have = 1; }
  return ps->cur;
}
static token_t p_take(pstate_t *ps) {
  token_t t = p_peek(ps);
  ps->have = 0;
  return t;
}

/* Provided by emit.inc (included via compile.inc) */
static uint64_t art_read(vm_t *vm, bitaddr_t ART, unsigned idx);

/* expr + compiler */
#include "expr.inc"
#include "compile.inc"

int main(int argc, char **argv) {
  const char *image = NULL;
  const char *in = NULL;
  const char *outpath = NULL;

  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--image") && i+1 < argc) image = argv[++i];
    else if (!strcmp(argv[i], "--in") && i+1 < argc) in = argv[++i];
    else if (!strcmp(argv[i], "--out") && i+1 < argc) outpath = argv[++i];
    else { usage(argv[0]); return 2; }
  }
  if (!image || !in || !outpath) { usage(argv[0]); return 2; }

  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) {
    fprintf(stderr, "forth0c: vm_init failed\n");
    return 1;
  }
  if (load_image(&vm, image) != 0) { vm_free(&vm); return 1; }

  bitaddr_t W = vm.workspace_base;
  bitaddr_t ART = (W + 512u + 7u) & ~(bitaddr_t)7u;

  /* compute WORDS_BASE + STEP same as mkimage std7_fixed */
  unsigned bsel = 0;
  while (((bitaddr_t)1u << bsel) < (bitaddr_t)vm.processor_bits) bsel++;
  if (bsel >= vm.addr_bits) { fprintf(stderr, "forth0c: cannot determine STEP\n"); vm_free(&vm); return 1; }
  bitaddr_t STEP = (bitaddr_t)1u << bsel;
  bitaddr_t words_region_pages = 144;  // was 128, now 144 for 32-bit gate words (slots 128-140)
  bitaddr_t words_region_bits = (bitaddr_t)words_region_pages * STEP;
  bitaddr_t align_bits = (bitaddr_t)1u << (bsel + 1u);
  bitaddr_t WORDS_BASE = (vm.space_bits - words_region_bits) & ~(align_bits - 1u);

  /* report TESTG(byte) for harness */
  uint64_t testg = art_read(&vm, ART, (unsigned)ART_TESTG);
  fprintf(stderr, "TESTG(byte)=%u\n", (unsigned)(testg / 8u));

  FILE *out = fopen(outpath, "wb");
  if (!out) { perror("fopen"); vm_free(&vm); return 1; }

  size_t len = 0;
  char *buf = read_file_all(in, &len);
  if (!buf) {
    fprintf(stderr, "forth0c: cannot read input: %s\n", in);
    fclose(out);
    vm_free(&vm);
    return 1;
  }

  lex_t lx;
  lx.path = in;
  lx.buf = buf;
  lx.len = len;
  lx.i = 0;
  lx.line = 1;

  pstate_t ps;
  memset(&ps, 0, sizeof(ps));
  ps.lx = &lx;
  ps.vm = &vm;
  ps.ART = ART;
  ps.art_count = (unsigned)ART_COUNT;

  /* built-in consts */
  const_set(&ps.consts, "ADDR_BITS", (uint64_t)vm.addr_bits);
  const_set(&ps.consts, "ADDR_BYTES", (uint64_t)(vm.addr_bits/8u));
  const_set(&ps.consts, "N_BITS", (uint64_t)vm.n_bits);
  const_set(&ps.consts, "INSTR_BITS", (uint64_t)vm.instr_bits);
  const_set(&ps.consts, "PROCESSOR_N", (uint64_t)vm.processor_n);
  const_set(&ps.consts, "PROCESSOR_BITS", (uint64_t)vm.processor_bits);
  const_set(&ps.consts, "WORKSPACE_BASE", (uint64_t)vm.workspace_base);
  const_set(&ps.consts, "SPACE_BITS", (uint64_t)vm.space_bits);
  const_set(&ps.consts, "STEP", (uint64_t)STEP);
  const_set(&ps.consts, "WORDS_BASE", (uint64_t)WORDS_BASE);
  const_set(&ps.consts, "WORDS_PAGES", (uint64_t)words_region_pages);
  const_set(&ps.consts, "OFF_N", (uint64_t)vm.off_n);
  const_set(&ps.consts, "OFF_DST", (uint64_t)vm.off_dst);
  const_set(&ps.consts, "OFF_SRC", (uint64_t)vm.off_src);
  const_set(&ps.consts, "ART_BASE", (uint64_t)ART);

  /* page/if state */
  ps.page_addr = 0;
  ps.page_slot = 0;
  ps.if_depth = -1;
  ps.flags = 0;

  compile_stream(&ps, out);

  macro_free_all(&ps.macros);

  for (size_t i = 0; i < ps.consts.n; i++) free(ps.consts.v[i].name);
  free(ps.consts.v);

  free(buf);
  fclose(out);
  vm_free(&vm);
  return 0;
}
