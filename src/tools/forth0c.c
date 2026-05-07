// forth0c.c — host-side minimal Forth0 token compiler (.f0 -> .tok).
//
// .f0 format:
//   - whitespace-separated tokens
//   - comments: '#' or '\' to end of line
//   - directive: include "path/to/file.f0"    (path resolved relative to current file)
//   - directive: const NAME <expr>            (compile-time constant)
//   - directive: emit <expr>                  (emit raw token value)
//   - directive: copybits <n> <dst> <src>     (emit LITN/LITD/LITS/COPY)
//   - directive: setbit <dst_bitaddr> <0|1>   (copy 1 bit from CONST0/CONST1)
//   - directive: setbyte <byte_bitaddr> <u8>  (8x setbit, MSB-first)
//   - directive: set24 <base_bitaddr> <u24>   (3x setbyte, big-endian)
//
//   - words: identifiers resolved via ART table from --image (e.g. LITN, COPY, HALT)
//   - immediates: after LIT* words, next is an expression
//   - expressions: numbers (dec/0x...), symbols (ART names), consts, + - * / and parentheses
//
// Emits addr-sized big-endian tokens.
// Prints to stderr: TESTG(byte)=<offset> (for bash harness).

#include "space.h"
#include "mkimage/std7_fixed/artifacts.h" // ART_* enum + ART_COUNT
#include <ctype.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
  const char *name;
  unsigned art_idx;
} sym_t;

static const sym_t g_syms[] = {
  /* core cells/words/vars */
  {"HEAD_CELL", ART_HEAD_CELL}, {"ART_HEAD_CELL", ART_HEAD_CELL},
  {"NEXT_IMG",  ART_NEXT_IMG},  {"ART_NEXT_IMG",  ART_NEXT_IMG},
  {"VAR_IP",    ART_VAR_IP},    {"ART_VAR_IP",    ART_VAR_IP},

  {"WORD_SETUP",  ART_WORD_SETUP},  {"ART_WORD_SETUP",  ART_WORD_SETUP},  {"SETUP",  ART_WORD_SETUP},
  {"WORD_INREQ",  ART_WORD_INREQ},  {"ART_WORD_INREQ",  ART_WORD_INREQ},  {"INREQ",  ART_WORD_INREQ},
  {"WORD_OUTREQ", ART_WORD_OUTREQ}, {"ART_WORD_OUTREQ", ART_WORD_OUTREQ}, {"OUTREQ", ART_WORD_OUTREQ},
  {"WORD_HALT",   ART_WORD_HALT},   {"ART_WORD_HALT",   ART_WORD_HALT},   {"HALT",   ART_WORD_HALT},

  {"VAR_LOOP",     ART_VAR_LOOP},     {"ART_VAR_LOOP",     ART_VAR_LOOP},
  {"WORD_SAVEIP",  ART_WORD_SAVEIP},  {"ART_WORD_SAVEIP",  ART_WORD_SAVEIP},  {"SAVEIP",  ART_WORD_SAVEIP},
  {"WORD_JMP",     ART_WORD_JMP},     {"ART_WORD_JMP",     ART_WORD_JMP},     {"JMP",     ART_WORD_JMP},
  {"WORD_SETOLEN", ART_WORD_SETOLEN}, {"ART_WORD_SETOLEN", ART_WORD_SETOLEN}, {"SETOLEN", ART_WORD_SETOLEN},
  {"WORD_IFGOT0",  ART_WORD_IFGOT0},  {"ART_WORD_IFGOT0",  ART_WORD_IFGOT0},  {"IFGOT0",  ART_WORD_IFGOT0},

  {"VAR_N",   ART_VAR_N},   {"ART_VAR_N",   ART_VAR_N},
  {"VAR_DST", ART_VAR_DST}, {"ART_VAR_DST", ART_VAR_DST},
  {"VAR_SRC", ART_VAR_SRC}, {"ART_VAR_SRC", ART_VAR_SRC},

  {"WORD_LITN",  ART_WORD_LITN},  {"ART_WORD_LITN",  ART_WORD_LITN},  {"LITN",  ART_WORD_LITN},
  {"WORD_LITD",  ART_WORD_LITD},  {"ART_WORD_LITD",  ART_WORD_LITD},  {"LITD",  ART_WORD_LITD},
  {"WORD_LITS",  ART_WORD_LITS},  {"ART_WORD_LITS",  ART_WORD_LITS},  {"LITS",  ART_WORD_LITS},
  {"WORD_COPY",  ART_WORD_COPY},  {"ART_WORD_COPY",  ART_WORD_COPY},  {"COPY",  ART_WORD_COPY},
  {"WORD_LITIP", ART_WORD_LITIP}, {"ART_WORD_LITIP", ART_WORD_LITIP}, {"LITIP", ART_WORD_LITIP},

  {"BA", ART_BA}, {"ART_BA", ART_BA},
  {"BB", ART_BB}, {"ART_BB", ART_BB},
  {"BC", ART_BC}, {"ART_BC", ART_BC},
  {"BR", ART_BR}, {"ART_BR", ART_BR},
  {"T0", ART_T0}, {"ART_T0", ART_T0},
  {"T1", ART_T1}, {"ART_T1", ART_T1},

  {"WORD_BNOT", ART_WORD_BNOT}, {"ART_WORD_BNOT", ART_WORD_BNOT}, {"BNOT", ART_WORD_BNOT},
  {"WORD_BAND", ART_WORD_BAND}, {"ART_WORD_BAND", ART_WORD_BAND}, {"BAND", ART_WORD_BAND},

  {"CONST1", ART_CONST1}, {"ART_CONST1", ART_CONST1},
  {"CONST0", ART_CONST0}, {"ART_CONST0", ART_CONST0},
  {"TESTG",  ART_TESTG},  {"ART_TESTG",  ART_TESTG},

  {"WORD_BOR",  ART_WORD_BOR},  {"ART_WORD_BOR",  ART_WORD_BOR},  {"BOR",  ART_WORD_BOR},
  {"WORD_BXOR", ART_WORD_BXOR}, {"ART_WORD_BXOR", ART_WORD_BXOR}, {"BXOR", ART_WORD_BXOR},

  /* 2a */
  {"WORD_ADD24", ART_WORD_ADD24}, {"ART_WORD_ADD24", ART_WORD_ADD24}, {"ADD24", ART_WORD_ADD24},
  {"VAR_A24",    ART_VAR_A24},    {"ART_VAR_A24",    ART_VAR_A24},
  {"VAR_B24",    ART_VAR_B24},    {"ART_VAR_B24",    ART_VAR_B24},
  {"VAR_SUM24",  ART_VAR_SUM24},  {"ART_VAR_SUM24",  ART_VAR_SUM24},
  {"VAR_COUT",   ART_VAR_COUT},   {"ART_VAR_COUT",   ART_VAR_COUT},
  {"WORD_EQ24",  ART_WORD_EQ24},  {"ART_WORD_EQ24",  ART_WORD_EQ24},  {"EQ24", ART_WORD_EQ24},
  {"VAR_EQ",     ART_VAR_EQ},     {"ART_VAR_EQ",     ART_VAR_EQ},
  {"WORD_LT24",  ART_WORD_LT24},  {"ART_WORD_LT24",  ART_WORD_LT24},  {"LT24", ART_WORD_LT24},
  {"VAR_LT",     ART_VAR_LT},     {"ART_VAR_LT",     ART_VAR_LT},

  /* 2b pointers */
  {"WORD_LITAP", ART_WORD_LITAP}, {"ART_WORD_LITAP", ART_WORD_LITAP}, {"LITAP", ART_WORD_LITAP},
  {"WORD_LITBP", ART_WORD_LITBP}, {"ART_WORD_LITBP", ART_WORD_LITBP}, {"LITBP", ART_WORD_LITBP},
  {"WORD_LITRP", ART_WORD_LITRP}, {"ART_WORD_LITRP", ART_WORD_LITRP}, {"LITRP", ART_WORD_LITRP},
  {"VAR_AP",     ART_VAR_AP},     {"ART_VAR_AP",     ART_VAR_AP},
  {"VAR_BP",     ART_VAR_BP},     {"ART_VAR_BP",     ART_VAR_BP},
  {"VAR_RP",     ART_VAR_RP},     {"ART_VAR_RP",     ART_VAR_RP},
  {"OFFTAB",     ART_OFFTAB},     {"ART_OFFTAB",     ART_OFFTAB},
  {"WORD_EQ24P", ART_WORD_EQ24P}, {"ART_WORD_EQ24P", ART_WORD_EQ24P}, {"EQ24P", ART_WORD_EQ24P},

  /* scratch/devices */
  {"TESTSCR_BASE", ART_TESTSCR_BASE}, {"ART_TESTSCR_BASE", ART_TESTSCR_BASE},
  {"TESTSCR_END",  ART_TESTSCR_END},  {"ART_TESTSCR_END",  ART_TESTSCR_END},
  {"BUS_BASE",     ART_BUS_BASE},     {"ART_BUS_BASE",     ART_BUS_BASE},
  {"TERM0_DESC",   ART_TERM0_DESC},   {"ART_TERM0_DESC",   ART_TERM0_DESC},

  /* ptrprims */
  {"WORD_LOAD24AP",  ART_WORD_LOAD24AP},  {"ART_WORD_LOAD24AP",  ART_WORD_LOAD24AP},  {"LOAD24AP",  ART_WORD_LOAD24AP},
  {"WORD_LOAD24BP",  ART_WORD_LOAD24BP},  {"ART_WORD_LOAD24BP",  ART_WORD_LOAD24BP},  {"LOAD24BP",  ART_WORD_LOAD24BP},
  {"WORD_STORE24RP", ART_WORD_STORE24RP}, {"ART_WORD_STORE24RP", ART_WORD_STORE24RP}, {"STORE24RP", ART_WORD_STORE24RP},
};

typedef struct {
  char *name;
  uint64_t val;
} const_ent_t;

typedef struct {
  const_ent_t *v;
  size_t n, cap;
} consttab_t;

static void usage(const char *a0) {
  fprintf(stderr, "usage: %s --image std7.bin --in prog.f0 --out prog.tok\n", a0);
}

static int load_image(vm_t *vm, const char *path) {
  FILE *f = fopen(path, "rb");
  if (!f) { perror("fopen"); return -1; }
  if (fseek(f, 0, SEEK_END) != 0) { perror("fseek"); fclose(f); return -1; }
  long sz = ftell(f);
  if (sz < 0) { perror("ftell"); fclose(f); return -1; }
  rewind(f);
  if ((size_t)sz != vm->space_bytes) {
    fprintf(stderr, "size mismatch: file=%ld expected=%zu\n", sz, vm->space_bytes);
    fclose(f);
    return -1;
  }
  if (fread(vm->space, 1, vm->space_bytes, f) != vm->space_bytes) {
    perror("fread"); fclose(f); return -1;
  }
  fclose(f);
  return 0;
}

static int str_ieq(const char *a, const char *b) {
  while (*a && *b) {
    unsigned ca = (unsigned char)*a++;
    unsigned cb = (unsigned char)*b++;
    if (tolower(ca) != tolower(cb)) return 0;
  }
  return *a == 0 && *b == 0;
}

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
    if (strcmp(ct->v[i].name, name) == 0) {
      ct->v[i].val = val;
      return;
    }
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
    if (strcmp(ct->v[i].name, name) == 0) {
      *out = ct->v[i].val;
      return 1;
    }
  }
  return 0;
}

static int sym_lookup_art_idx(const char *name, unsigned *out_idx) {
  /* allow ART[NN] */
  if ((name[0]=='A'||name[0]=='a') && (name[1]=='R'||name[1]=='r') && (name[2]=='T'||name[2]=='t') && name[3]=='[') {
    const char *p = name + 4;
    char *e = NULL;
    errno = 0;
    unsigned long v = strtoul(p, &e, 10);
    if (errno == 0 && e && *e == ']') {
      *out_idx = (unsigned)v;
      return 1;
    }
  }

  for (size_t i = 0; i < sizeof(g_syms)/sizeof(g_syms[0]); i++) {
    if (str_ieq(name, g_syms[i].name)) {
      *out_idx = g_syms[i].art_idx;
      return 1;
    }
  }
  return 0;
}

static uint64_t art_read(vm_t *vm, bitaddr_t ART, unsigned idx) {
  return vm_read_uint(vm, ART + (bitaddr_t)idx * (bitaddr_t)vm->addr_bits, vm->addr_bits);
}

static void write_be(FILE *f, uint64_t v, unsigned nbytes) {
  for (unsigned i = 0; i < nbytes; i++) {
    unsigned shift = 8u*(nbytes-1u-i);
    fputc((int)((v >> shift) & 0xFFu), f);
  }
}

static void emit_u(vm_t *vm, FILE *out, uint64_t v) {
  unsigned nbytes = vm->addr_bits / 8u;
  if (nbytes == 0 || (vm->addr_bits % 8u) != 0) {
    fprintf(stderr, "forth0c: unsupported addr_bits=%u\n", vm->addr_bits);
    exit(1);
  }
  if (vm->addr_bits < 64u) {
    uint64_t mask = (1ull << vm->addr_bits) - 1ull;
    v &= mask;
  }
  write_be(out, v, nbytes);
}

/* -------------------- lexer -------------------- */

typedef enum { TK_EOF=0, TK_ID, TK_NUM, TK_OP, TK_STR } tk_kind_t;

typedef struct {
  tk_kind_t k;
  char s[512];     /* for ID/STR */
  uint64_t num;    /* for NUM */
  char op;         /* for OP */
} token_t;

typedef struct {
  const char *path;
  char *buf;
  size_t len;
  size_t i;
  unsigned line;
} lex_t;

static void lex_die(const lex_t *lx, const char *msg) {
  fprintf(stderr, "forth0c: %s:%u: %s\n", lx->path, lx->line, msg);
  exit(1);
}

static int is_id0(int c) { return isalpha(c) || c=='_' ; }
static int is_id1(int c) { return isalnum(c) || c=='_' || c=='[' || c==']'; }

static void lex_skip_ws_and_comments(lex_t *lx) {
  for (;;) {
    while (lx->i < lx->len) {
      char c = lx->buf[lx->i];
      if (c==' ' || c=='\t' || c=='\r' || c=='\n') {
        if (c=='\n') lx->line++;
        lx->i++;
        continue;
      }
      break;
    }
    if (lx->i >= lx->len) return;

    char c = lx->buf[lx->i];

    /* line comment: # ... or \ ... */
    if (c == '#' || c == '\\') {
      while (lx->i < lx->len && lx->buf[lx->i] != '\n') lx->i++;
      continue;
    }

    return;
  }
}

static token_t lex_next(lex_t *lx) {
  lex_skip_ws_and_comments(lx);

  token_t t;
  memset(&t, 0, sizeof(t));

  if (lx->i >= lx->len) { t.k = TK_EOF; return t; }

  char c = lx->buf[lx->i];

  /* string */
  if (c == '"') {
    lx->i++;
    size_t j = 0;
    while (lx->i < lx->len) {
      char d = lx->buf[lx->i++];
      if (d == '"') break;
      if (d == '\\') {
        if (lx->i >= lx->len) lex_die(lx, "unterminated string escape");
        char e = lx->buf[lx->i++];
        if (e == 'n') d = '\n';
        else if (e == 't') d = '\t';
        else if (e == '"' || e == '\\') d = e;
        else lex_die(lx, "unsupported string escape");
      }
      if (j + 1 >= sizeof(t.s)) lex_die(lx, "string too long");
      t.s[j++] = d;
    }
    t.s[j] = 0;
    t.k = TK_STR;
    return t;
  }

  /* operators */
  if (c=='+' || c=='-' || c=='*' || c=='/' || c=='(' || c==')') {
    t.k = TK_OP;
    t.op = c;
    lx->i++;
    return t;
  }

  /* number */
  if (isdigit((unsigned char)c)) {
    char tmp[256];
    size_t j = 0;
    while (lx->i < lx->len && j+1 < sizeof(tmp)) {
      char d = lx->buf[lx->i];
      if (!(isalnum((unsigned char)d) || d=='x' || d=='X')) break;
      tmp[j++] = d;
      lx->i++;
    }
    tmp[j] = 0;

    char *e = NULL;
    errno = 0;
    uint64_t v = strtoull(tmp, &e, 0);
    if (errno != 0 || !e || *e != 0) lex_die(lx, "bad number");
    t.k = TK_NUM;
    t.num = v;
    return t;
  }

  /* identifier */
  if (is_id0((unsigned char)c)) {
    size_t j = 0;
    while (lx->i < lx->len && is_id1((unsigned char)lx->buf[lx->i]) && j+1 < sizeof(t.s)) {
      t.s[j++] = lx->buf[lx->i++];
    }
    t.s[j] = 0;
    t.k = TK_ID;
    return t;
  }

  lex_die(lx, "unexpected character");
  t.k = TK_EOF;
  return t;
}

/* -------------------- parser state -------------------- */

typedef struct {
  lex_t *lx;
  int have;
  token_t cur;
  vm_t *vm;
  bitaddr_t ART;
  unsigned art_count;
  consttab_t consts;
} pstate_t;

static token_t p_peek(pstate_t *ps) {
  if (!ps->have) {
    ps->cur = lex_next(ps->lx);
    ps->have = 1;
  }
  return ps->cur;
}

static token_t p_take(pstate_t *ps) {
  token_t t = p_peek(ps);
  ps->have = 0;
  return t;
}

static uint64_t parse_expr(pstate_t *ps);

static uint64_t parse_factor(pstate_t *ps) {
  token_t t = p_peek(ps);

  if (t.k == TK_OP && (t.op == '+' || t.op == '-')) {
    p_take(ps);
    uint64_t v = parse_factor(ps);
    if (t.op == '-') return (uint64_t)(0ull - v);
    return v;
  }

  if (t.k == TK_NUM) {
    p_take(ps);
    return t.num;
  }

  if (t.k == TK_ID) {
    p_take(ps);

    uint64_t cv = 0;
    if (const_get(&ps->consts, t.s, &cv)) return cv;

    unsigned idx = 0;
    if (!sym_lookup_art_idx(t.s, &idx)) {
      fprintf(stderr, "forth0c: %s:%u: unknown symbol: %s\n", ps->lx->path, ps->lx->line, t.s);
      exit(1);
    }
    if (idx >= ps->art_count) {
      fprintf(stderr, "forth0c: %s:%u: ART index out of range: %u (ART_COUNT=%u)\n",
              ps->lx->path, ps->lx->line, idx, ps->art_count);
      exit(1);
    }
    return art_read(ps->vm, ps->ART, idx);
  }

  if (t.k == TK_OP && t.op == '(') {
    p_take(ps);
    uint64_t v = parse_expr(ps);
    token_t r = p_take(ps);
    if (!(r.k == TK_OP && r.op == ')')) lex_die(ps->lx, "expected ')'");
    return v;
  }

  lex_die(ps->lx, "bad expression");
  return 0;
}

static uint64_t parse_term(pstate_t *ps) {
  uint64_t v = parse_factor(ps);
  for (;;) {
    token_t t = p_peek(ps);
    if (!(t.k == TK_OP && (t.op == '*' || t.op == '/'))) break;
    p_take(ps);
    uint64_t rhs = parse_factor(ps);
    if (t.op == '*') v = v * rhs;
    else {
      if (rhs == 0) lex_die(ps->lx, "division by zero");
      v = v / rhs;
    }
  }
  return v;
}

static uint64_t parse_expr(pstate_t *ps) {
  uint64_t v = parse_term(ps);
  for (;;) {
    token_t t = p_peek(ps);
    if (!(t.k == TK_OP && (t.op == '+' || t.op == '-'))) break;
    p_take(ps);
    uint64_t rhs = parse_term(ps);
    if (t.op == '+') v = v + rhs;
    else v = v - rhs;
  }
  return v;
}

/* -------------------- include handling -------------------- */

static char *read_file_all(const char *path, size_t *out_len) {
  FILE *f = fopen(path, "rb");
  if (!f) return NULL;
  if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return NULL; }
  long sz = ftell(f);
  if (sz < 0) { fclose(f); return NULL; }
  rewind(f);
  char *buf = (char*)malloc((size_t)sz + 1u);
  if (!buf) { fclose(f); return NULL; }
  if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) { free(buf); fclose(f); return NULL; }
  fclose(f);
  buf[(size_t)sz] = 0;
  if (out_len) *out_len = (size_t)sz;
  return buf;
}

static void path_dirname(const char *path, char *out, size_t out_sz) {
  const char *slash = strrchr(path, '/');
  const char *bslash = strrchr(path, '\\');
  const char *p = slash;
  if (!p || (bslash && bslash > p)) p = bslash;

  if (!p) { snprintf(out, out_sz, "."); return; }

  size_t n = (size_t)(p - path);
  if (n == 0) n = 1; /* "/" */
  if (n + 1 > out_sz) n = out_sz - 1;
  memcpy(out, path, n);
  out[n] = 0;
}

static void path_join(const char *dir, const char *rel, char *out, size_t out_sz) {
  if (!dir || !*dir || strcmp(dir, ".") == 0) { snprintf(out, out_sz, "%s", rel); return; }
  snprintf(out, out_sz, "%s/%s", dir, rel);
}

static void compile_one_file(pstate_t *ps, const char *path, FILE *out);

/* -------------------- emit helpers -------------------- */

static uint64_t artv(pstate_t *ps, unsigned idx) {
  if (idx >= ps->art_count) {
    fprintf(stderr, "forth0c: internal: ART idx out of range: %u\n", idx);
    exit(1);
  }
  return art_read(ps->vm, ps->ART, idx);
}

static void emit_word_by_artidx(pstate_t *ps, FILE *out, unsigned word_art_idx) {
  uint64_t w = artv(ps, word_art_idx);
  if (!w) {
    fprintf(stderr, "forth0c: %s:%u: ART[%u] is 0 (word missing)\n", ps->lx->path, ps->lx->line, word_art_idx);
    exit(1);
  }
  emit_u(ps->vm, out, w);
}

static void emit_lit_word_imm(pstate_t *ps, FILE *out, unsigned lit_word_art_idx, uint64_t imm) {
  emit_word_by_artidx(ps, out, lit_word_art_idx);
  emit_u(ps->vm, out, imm);
}

/* -------------------- compiler -------------------- */

static int word_needs_imm(const char *name) {
  return str_ieq(name, "LITN")  || str_ieq(name, "WORD_LITN")  || str_ieq(name, "ART_WORD_LITN") ||
         str_ieq(name, "LITD")  || str_ieq(name, "WORD_LITD")  || str_ieq(name, "ART_WORD_LITD") ||
         str_ieq(name, "LITS")  || str_ieq(name, "WORD_LITS")  || str_ieq(name, "ART_WORD_LITS") ||
         str_ieq(name, "LITIP") || str_ieq(name, "WORD_LITIP") || str_ieq(name, "ART_WORD_LITIP") ||
         str_ieq(name, "LITAP") || str_ieq(name, "WORD_LITAP") || str_ieq(name, "ART_WORD_LITAP") ||
         str_ieq(name, "LITBP") || str_ieq(name, "WORD_LITBP") || str_ieq(name, "ART_WORD_LITBP") ||
         str_ieq(name, "LITRP") || str_ieq(name, "WORD_LITRP") || str_ieq(name, "ART_WORD_LITRP");
}

static void do_copybits(pstate_t *ps, FILE *out, uint64_t n, uint64_t dst, uint64_t src) {
  emit_lit_word_imm(ps, out, ART_WORD_LITN, n);
  emit_lit_word_imm(ps, out, ART_WORD_LITD, dst);
  emit_lit_word_imm(ps, out, ART_WORD_LITS, src);
  emit_word_by_artidx(ps, out, ART_WORD_COPY);
}

static void do_setbit(pstate_t *ps, FILE *out, uint64_t dst_bitaddr, int val01) {
  uint64_t src = artv(ps, val01 ? ART_CONST1 : ART_CONST0);
  do_copybits(ps, out, 1u, dst_bitaddr, src);
}

static void do_setbyte(pstate_t *ps, FILE *out, uint64_t byte_bitaddr, uint64_t u8) {
  u8 &= 0xFFu;
  for (unsigned off = 0; off < 8u; off++) {
    unsigned bit = (unsigned)((u8 >> (7u - off)) & 1u);
    do_setbit(ps, out, byte_bitaddr + (uint64_t)off, (int)bit);
  }
}

static void do_set24(pstate_t *ps, FILE *out, uint64_t base_bitaddr, uint64_t u24) {
  u24 &= 0xFFFFFFu;
  uint64_t b0 = (u24 >> 16) & 0xFFu;
  uint64_t b1 = (u24 >>  8) & 0xFFu;
  uint64_t b2 = (u24 >>  0) & 0xFFu;
  do_setbyte(ps, out, base_bitaddr + 0u*8u, b0);
  do_setbyte(ps, out, base_bitaddr + 1u*8u, b1);
  do_setbyte(ps, out, base_bitaddr + 2u*8u, b2);
}

static void compile_stream(pstate_t *ps, FILE *out) {
  for (;;) {
    token_t t = p_peek(ps);
    if (t.k == TK_EOF) return;
    if (t.k != TK_ID) lex_die(ps->lx, "expected word/directive");

    t = p_take(ps);

    /* directives */
    if (str_ieq(t.s, "include")) {
      token_t p = p_take(ps);
      if (!(p.k == TK_STR || p.k == TK_ID)) lex_die(ps->lx, "include expects a string or bare token");
      char dir[512], full[1024];
      path_dirname(ps->lx->path, dir, sizeof(dir));
      path_join(dir, p.s, full, sizeof(full));
      compile_one_file(ps, full, out);
      continue;
    }

    if (str_ieq(t.s, "const")) {
      token_t n = p_take(ps);
      if (n.k != TK_ID) lex_die(ps->lx, "const expects NAME");
      uint64_t v = parse_expr(ps);
      const_set(&ps->consts, n.s, v);
      continue;
    }

    if (str_ieq(t.s, "emit")) {
      uint64_t v = parse_expr(ps);
      emit_u(ps->vm, out, v);
      continue;
    }

    if (str_ieq(t.s, "copybits")) {
      uint64_t n = parse_expr(ps);
      uint64_t dst = parse_expr(ps);
      uint64_t src = parse_expr(ps);
      do_copybits(ps, out, n, dst, src);
      continue;
    }

    if (str_ieq(t.s, "setbit")) {
      uint64_t dst = parse_expr(ps);
      uint64_t v = parse_expr(ps);
      do_setbit(ps, out, dst, (v != 0));
      continue;
    }

    if (str_ieq(t.s, "setbyte")) {
      uint64_t dst = parse_expr(ps);
      uint64_t v = parse_expr(ps);
      do_setbyte(ps, out, dst, v);
      continue;
    }

    if (str_ieq(t.s, "set24")) {
      uint64_t dst = parse_expr(ps);
      uint64_t v = parse_expr(ps);
      do_set24(ps, out, dst, v);
      continue;
    }

    /* normal word emission by ART */
    unsigned idx = 0;
    if (!sym_lookup_art_idx(t.s, &idx)) {
      fprintf(stderr, "forth0c: %s:%u: unknown word: %s\n", ps->lx->path, ps->lx->line, t.s);
      exit(1);
    }
    if (idx >= ps->art_count) {
      fprintf(stderr, "forth0c: %s:%u: ART index out of range: %u (ART_COUNT=%u)\n",
              ps->lx->path, ps->lx->line, idx, ps->art_count);
      exit(1);
    }
    uint64_t word_addr = art_read(ps->vm, ps->ART, idx);
    if (word_addr == 0) {
      fprintf(stderr, "forth0c: %s:%u: ART[%u] resolved to 0 for '%s'\n",
              ps->lx->path, ps->lx->line, idx, t.s);
      exit(1);
    }
    emit_u(ps->vm, out, word_addr);

    if (word_needs_imm(t.s)) {
      uint64_t imm = parse_expr(ps);
      emit_u(ps->vm, out, imm);
    }
  }
}

static void compile_one_file(pstate_t *ps, const char *path, FILE *out) {
  size_t len = 0;
  char *buf = read_file_all(path, &len);
  if (!buf) {
    fprintf(stderr, "forth0c: cannot read include file: %s\n", path);
    exit(1);
  }

  lex_t lx;
  lx.path = path;
  lx.buf = buf;
  lx.len = len;
  lx.i = 0;
  lx.line = 1;

  /* save/replace lexer state */
  lex_t *saved_lx = ps->lx;
  int saved_have = ps->have;
  token_t saved_cur = ps->cur;

  ps->lx = &lx;
  ps->have = 0;

  compile_stream(ps, out);

  /* restore */
  ps->lx = saved_lx;
  ps->have = saved_have;
  ps->cur = saved_cur;

  free(buf);
}

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

  /* report TESTG(byte) like other mktok_test_* tools */
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

  /* handy built-in consts */
  const_set(&ps.consts, "ADDR_BITS", (uint64_t)vm.addr_bits);
  const_set(&ps.consts, "ADDR_BYTES", (uint64_t)(vm.addr_bits/8u));
  const_set(&ps.consts, "WORKSPACE_BASE", (uint64_t)vm.workspace_base);

  compile_stream(&ps, out);

  for (size_t i = 0; i < ps.consts.n; i++) free(ps.consts.v[i].name);
  free(ps.consts.v);

  free(buf);
  fclose(out);
  vm_free(&vm);
  return 0;
}
