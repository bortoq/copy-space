// forth0c.c — host-side minimal Forth0 token compiler (.f0 -> .tok).
// Goal: stop writing token-generators in C; write programs/tests as text.
//
// Format (.f0):
//   - whitespace-separated tokens
//   - comments: '#' or '\' to end of line; also '( ... )' comments
//   - directive:  include path/to/file.f0
//   - words: identifiers resolved via ART table from --image
//   - immediates: for LIT* words, the next expression is emitted as immediate
//   - expressions: numbers (dec/0x...), symbols, + - * / and parentheses
//
// Example:
//   LITN 1
//   LITD TESTG
//   LITS CONST1
//   COPY
//   HALT
//
// Prints to stderr: TESTG(byte)=<offset> (for bash harness parity with mktok_test_*).

#include "space.h"
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
  {"HEAD_CELL", 0}, {"ART_HEAD_CELL", 0},
  {"NEXT_IMG",  1}, {"ART_NEXT_IMG",  1},
  {"VAR_IP",    2}, {"ART_VAR_IP",    2},

  {"WORD_SETUP",  4}, {"ART_WORD_SETUP",  4}, {"SETUP",  4},
  {"WORD_INREQ",  5}, {"ART_WORD_INREQ",  5}, {"INREQ",  5},
  {"WORD_OUTREQ", 6}, {"ART_WORD_OUTREQ", 6}, {"OUTREQ", 6},
  {"WORD_HALT",   7}, {"ART_WORD_HALT",   7}, {"HALT",   7},

  {"VAR_LOOP",     20}, {"ART_VAR_LOOP",     20},
  {"WORD_SAVEIP",  21}, {"ART_WORD_SAVEIP",  21}, {"SAVEIP", 21},
  {"WORD_JMP",     22}, {"ART_WORD_JMP",     22}, {"JMP",    22},
  {"WORD_SETOLEN", 23}, {"ART_WORD_SETOLEN", 23}, {"SETOLEN",23},
  {"WORD_IFGOT0",  24}, {"ART_WORD_IFGOT0",  24}, {"IFGOT0", 24},

  {"VAR_N",   25}, {"ART_VAR_N",   25},
  {"VAR_DST", 26}, {"ART_VAR_DST", 26},
  {"VAR_SRC", 27}, {"ART_VAR_SRC", 27},

  {"WORD_LITN",  28}, {"ART_WORD_LITN",  28}, {"LITN",  28},
  {"WORD_LITD",  29}, {"ART_WORD_LITD",  29}, {"LITD",  29},
  {"WORD_LITS",  30}, {"ART_WORD_LITS",  30}, {"LITS",  30},
  {"WORD_COPY",  31}, {"ART_WORD_COPY",  31}, {"COPY",  31},
  {"WORD_LITIP", 32}, {"ART_WORD_LITIP", 32}, {"LITIP", 32},

  {"BA", 33}, {"ART_BA", 33},
  {"BB", 34}, {"ART_BB", 34},
  {"BC", 35}, {"ART_BC", 35},
  {"BR", 36}, {"ART_BR", 36},
  {"T0", 37}, {"ART_T0", 37},
  {"T1", 38}, {"ART_T1", 38},

  {"WORD_BNOT", 39}, {"ART_WORD_BNOT", 39}, {"BNOT", 39},
  {"WORD_BAND", 40}, {"ART_WORD_BAND", 40}, {"BAND", 40},

  {"CONST1", 41}, {"ART_CONST1", 41},
  {"CONST0", 42}, {"ART_CONST0", 42},
  {"TESTG",  43}, {"ART_TESTG",  43},

  {"WORD_BOR",  44}, {"ART_WORD_BOR",  44}, {"BOR",  44},
  {"WORD_BXOR", 45}, {"ART_WORD_BXOR", 45}, {"BXOR", 45},

  /* 2a */
  {"WORD_ADD24", 46}, {"ART_WORD_ADD24", 46}, {"ADD24", 46},
  {"VAR_A24",    47}, {"ART_VAR_A24",    47},
  {"VAR_B24",    48}, {"ART_VAR_B24",    48},
  {"VAR_SUM24",  49}, {"ART_VAR_SUM24",  49},
  {"VAR_COUT",   50}, {"ART_VAR_COUT",   50},
  {"WORD_EQ24",  51}, {"ART_WORD_EQ24",  51}, {"EQ24",  51},
  {"VAR_EQ",     52}, {"ART_VAR_EQ",     52},
  {"WORD_LT24",  53}, {"ART_WORD_LT24",  53}, {"LT24",  53},
  {"VAR_LT",     54}, {"ART_VAR_LT",     54},

  /* 2b pointers */
  {"WORD_LITAP", 55}, {"ART_WORD_LITAP", 55}, {"LITAP", 55},
  {"WORD_LITBP", 56}, {"ART_WORD_LITBP", 56}, {"LITBP", 56},
  {"WORD_LITRP", 57}, {"ART_WORD_LITRP", 57}, {"LITRP", 57},
  {"VAR_AP",     58}, {"ART_VAR_AP",     58},
  {"VAR_BP",     59}, {"ART_VAR_BP",     59},
  {"VAR_RP",     60}, {"ART_VAR_RP",     60},
  {"OFFTAB",     61}, {"ART_OFFTAB",     61},
  {"WORD_EQ24P", 62}, {"ART_WORD_EQ24P", 62}, {"EQ24P", 62},

  /* scratch/devices */
  {"TESTSCR_BASE", 63}, {"ART_TESTSCR_BASE", 63},
  {"TESTSCR_END",  64}, {"ART_TESTSCR_END",  64},
  {"BUS_BASE",     65}, {"ART_BUS_BASE",     65},
  {"TERM0_DESC",   66}, {"ART_TERM0_DESC",   66},

  /* ptrprims */
  {"WORD_LOAD24AP",  67}, {"ART_WORD_LOAD24AP",  67}, {"LOAD24AP", 67},
  {"WORD_LOAD24BP",  68}, {"ART_WORD_LOAD24BP",  68}, {"LOAD24BP", 68},
  {"WORD_STORE24RP", 69}, {"ART_WORD_STORE24RP", 69}, {"STORE24RP",69},
};

static void usage(const char *a0) {
  fprintf(stderr,
          "usage: %s --image std7.bin --in prog.f0 --out prog.tok\n"
          "notes:\n"
          "  - emits addr-sized big-endian tokens\n"
          "  - prints TESTG(byte)=... to stderr\n",
          a0);
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

static int sym_lookup_art_idx(const char *name, unsigned *out_idx) {
  /* allow ART[NN] */
  if (!strncasecmp(name, "ART[", 4)) {
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

/* -------------------- lexer -------------------- */

typedef enum { TK_EOF=0, TK_ID, TK_NUM, TK_OP } tk_kind_t;

typedef struct {
  tk_kind_t k;
  char s[256];     /* for ID */
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

    /* line comment: # ... */
    if (c == '#' || c == '\\') {
      while (lx->i < lx->len && lx->buf[lx->i] != '\n') lx->i++;
      continue;
    }

    /* paren comment: ( ... ) */
    if (c == '(') {
      lx->i++;
      while (lx->i < lx->len && lx->buf[lx->i] != ')') {
        if (lx->buf[lx->i] == '\n') lx->line++;
        lx->i++;
      }
      if (lx->i < lx->len && lx->buf[lx->i] == ')') lx->i++;
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

  /* operators */
  if (c=='+' || c=='-' || c=='*' || c=='/' || c=='(' || c==')') {
    t.k = TK_OP;
    t.op = c;
    lx->i++;
    return t;
  }

  /* number */
  if (isdigit((unsigned char)c)) {
    size_t j = 0;
    char tmp[256];
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

/* -------------------- expression parser -------------------- */

typedef struct {
  lex_t *lx;
  int have;
  token_t cur;
  vm_t *vm;
  bitaddr_t ART;
  unsigned art_count;
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
  size_t n = strlen(path);
  size_t cut = n;
  while (cut > 0 && path[cut-1] != '/' && path[cut-1] != '\\') cut--;
  if (cut == 0) {
    snprintf(out, out_sz, ".");
  } else {
    if (cut >= out_sz) cut = out_sz-1;
    memcpy(out, path, cut);
    out[cut ? cut-1 : 0] = (cut ? out[cut-1] : 0); /* no-op to silence -Wmaybe-uninitialized */
    out[cut] = 0;
    /* trim trailing slash */
    while (cut > 0 && (out[cut-1] == '/' || out[cut-1] == '\\')) out[--cut] = 0;
    if (cut == 0) snprintf(out, out_sz, ".");
  }
}

static void path_join(const char *dir, const char *rel, char *out, size_t out_sz) {
  if (!dir || !*dir || strcmp(dir, ".") == 0) {
    snprintf(out, out_sz, "%s", rel);
    return;
  }
  snprintf(out, out_sz, "%s/%s", dir, rel);
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

static void emit_u(vm_t *vm, FILE *out, uint64_t v) {
  unsigned nbytes = vm->addr_bits / 8u;
  if (nbytes == 0 || (vm->addr_bits % 8u) != 0) {
    fprintf(stderr, "forth0c: unsupported addr_bits=%u (expected multiple of 8)\n", vm->addr_bits);
    exit(1);
  }
  if (vm->addr_bits < 64u) {
    uint64_t mask = (1ull << vm->addr_bits) - 1ull;
    v &= mask;
  }
  write_be(out, v, nbytes);
}

static void compile_one_file(pstate_t *ps, const char *path, FILE *out);

static void compile_stream(pstate_t *ps, FILE *out) {
  for (;;) {
    token_t t = p_peek(ps);
    if (t.k == TK_EOF) return;

    if (t.k != TK_ID) lex_die(ps->lx, "expected word/directive");

    t = p_take(ps);

    if (str_ieq(t.s, "include")) {
      token_t p = p_take(ps);
      if (p.k != TK_ID) lex_die(ps->lx, "include expects a path token");
      char dir[512], full[1024];
      path_dirname(ps->lx->path, dir, sizeof(dir));
      path_join(dir, p.s, full, sizeof(full));
      compile_one_file(ps, full, out);
      continue;
    }

    /* emit word token */
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

    /* optional immediate */
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

  /* swap lexer state */
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

  unsigned art_count = 0;
  /* ART_COUNT isn't itself stored in ART; use artifacts.h constant knowledge indirectly:
     We assume doc/tooling keeps ART_COUNT stable; for safety set a generous upper bound. */
  art_count = 256;

  /* report TESTG(byte) like other mktok_* tools */
  uint64_t testg = art_read(&vm, ART, 43u);
  fprintf(stderr, "TESTG(byte)=%u\n", (unsigned)(testg / 8u));

  FILE *out = fopen(outpath, "wb");
  if (!out) { perror("fopen"); vm_free(&vm); return 1; }

  /* main input file lexer */
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
  ps.art_count = art_count;

  compile_stream(&ps, out);

  free(buf);
  fclose(out);
  vm_free(&vm);
  return 0;
}
