/* forth0c_compile.inc — compiler, include, emit helpers, macros, for-loop (included into forth0c TU). */

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

static uint64_t art_read(vm_t *vm, bitaddr_t ART, unsigned idx) {
  return vm_read_uint(vm, ART + (bitaddr_t)idx * (bitaddr_t)vm->addr_bits, vm->addr_bits);
}

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

static int word_needs_imm(const char *name) {
  return str_ieq(name, "LITN")  || str_ieq(name, "WORD_LITN")  || str_ieq(name, "ART_WORD_LITN") ||
         str_ieq(name, "LITD")  || str_ieq(name, "WORD_LITD")  || str_ieq(name, "ART_WORD_LITD") ||
         str_ieq(name, "LITS")  || str_ieq(name, "WORD_LITS")  || str_ieq(name, "ART_WORD_LITS") ||
         str_ieq(name, "LITIP") || str_ieq(name, "WORD_LITIP") || str_ieq(name, "ART_WORD_LITIP") ||
         str_ieq(name, "LITAP") || str_ieq(name, "WORD_LITAP") || str_ieq(name, "ART_WORD_LITAP") ||
         str_ieq(name, "LITBP") || str_ieq(name, "WORD_LITBP") || str_ieq(name, "ART_WORD_LITBP") ||
         str_ieq(name, "LITRP") || str_ieq(name, "WORD_LITRP") || str_ieq(name, "ART_WORD_LITRP");
}

static int is_ptr_lit_word(const char *name) {
  return str_ieq(name, "LITAP") || str_ieq(name, "WORD_LITAP") || str_ieq(name, "ART_WORD_LITAP") ||
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

static void compile_stream(pstate_t *ps, FILE *out);
static void compile_one_file(pstate_t *ps, const char *path, FILE *out);

static void compile_from_buf(pstate_t *ps, const char *path, char *buf, size_t len, FILE *out) {
  lex_t lx;
  lx.path = path;
  lx.buf = buf;
  lx.len = len;
  lx.i = 0;
  lx.line = 1;

  lex_t *saved_lx = ps->lx;
  int saved_have = ps->have;
  token_t saved_cur = ps->cur;

  ps->lx = &lx;
  ps->have = 0;

  compile_stream(ps, out);

  ps->lx = saved_lx;
  ps->have = saved_have;
  ps->cur = saved_cur;
}

static void parse_macro_def(pstate_t *ps) {
  token_t name = p_take(ps);
  if (name.k != TK_ID) lex_die(ps->lx, "macro expects NAME");

  macro_t *m = macro_put(&ps->macros, name.s);

  /* params */
  token_t t = p_peek(ps);
  if (t.k == TK_OP && t.op == '(') {
    p_take(ps); /* '(' */
    token_t p = p_peek(ps);
    if (p.k == TK_OP && p.op == ')') {
      p_take(ps); /* ')' */
    } else {
      for (;;) {
        token_t pid = p_take(ps);
        if (pid.k != TK_ID) lex_die(ps->lx, "macro param must be identifier");

        m->params = (char**)xrealloc(m->params, (m->params_n + 1u) * sizeof(m->params[0]));
        m->params[m->params_n++] = xstrdup(pid.s);

        token_t sep = p_take(ps);
        if (sep.k == TK_OP && sep.op == ')') break;
        if (!(sep.k == TK_OP && sep.op == ',')) lex_die(ps->lx, "expected ',' or ')' in macro param list");
      }
    }
  }

  /* body until endmacro */
  for (;;) {
    token_t bt = p_take(ps);
    if (bt.k == TK_EOF) lex_die(ps->lx, "EOF inside macro (missing endmacro)");
    if (bt.k == TK_ID && str_ieq(bt.s, "endmacro")) break;
    macro_body_push(m, &bt);
  }
}

static void parse_macro_call(pstate_t *ps, FILE *out, const macro_t *m) {
  uint64_t *args = NULL;
  size_t args_n = 0;

  token_t t = p_peek(ps);
  if (t.k == TK_OP && t.op == '(') {
    p_take(ps); /* '(' */
    token_t p = p_peek(ps);
    if (p.k == TK_OP && p.op == ')') {
      p_take(ps); /* ')' */
    } else {
      for (;;) {
        uint64_t av = parse_expr(ps);
        args = (uint64_t*)xrealloc(args, (args_n + 1u) * sizeof(args[0]));
        args[args_n++] = av;

        token_t sep = p_take(ps);
        if (sep.k == TK_OP && sep.op == ')') break;
        if (!(sep.k == TK_OP && sep.op == ',')) lex_die(ps->lx, "expected ',' or ')' in macro call");
      }
    }
  } else {
    /* no parentheses -> zero args */
  }

  if (args_n != m->params_n) {
    fprintf(stderr, "forth0c: %s:%u: macro '%s' expects %zu args, got %zu\n",
            ps->lx->path, ps->lx->line, m->name, m->params_n, args_n);
    free(args);
    exit(1);
  }

  char *txt = macro_expand_text(m, args);
  compile_from_buf(ps, m->name, txt, strlen(txt), out);
  free(txt);
  free(args);
}

/* for VAR <start> <end> ... endfor
 * - VAR is substituted textually (like a 1-arg macro) with current iteration value.
 * - range is inclusive.
 */
static void parse_for_block(pstate_t *ps, FILE *out) {
  token_t var = p_take(ps);
  if (var.k != TK_ID) lex_die(ps->lx, "for expects loop variable name");

  uint64_t start = parse_expr(ps);
  uint64_t end   = parse_expr(ps);
  if (end < start) lex_die(ps->lx, "for: end < start");

  macro_t body;
  memset(&body, 0, sizeof(body));
  body.name = xstrdup("for_body");
  body.params = (char**)xrealloc(NULL, 1u * sizeof(char*));
  body.params[0] = xstrdup(var.s);
  body.params_n = 1;

  /* capture tokens until matching endfor (support nesting) */
  unsigned depth = 0;
  for (;;) {
    token_t bt = p_take(ps);
    if (bt.k == TK_EOF) lex_die(ps->lx, "EOF inside for (missing endfor)");

    if (bt.k == TK_ID && str_ieq(bt.s, "for")) {
      depth++;
      macro_body_push(&body, &bt);
      continue;
    }

    if (bt.k == TK_ID && str_ieq(bt.s, "endfor")) {
      if (depth == 0) break;
      depth--;
      macro_body_push(&body, &bt);
      continue;
    }

    macro_body_push(&body, &bt);
  }

  for (uint64_t i = start; i <= end; i++) {
    uint64_t arg = i;
    char *txt = macro_expand_text(&body, &arg);
    compile_from_buf(ps, "for", txt, strlen(txt), out);
    free(txt);
  }

  macro_free(&body);
}

static void compile_stream(pstate_t *ps, FILE *out) {
  for (;;) {
    token_t t = p_peek(ps);
    if (t.k == TK_EOF) return;
    if (t.k != TK_ID) lex_die(ps->lx, "expected word/directive");

    t = p_take(ps);

    /* macro def */
    if (str_ieq(t.s, "macro")) {
      parse_macro_def(ps);
      continue;
    }

    /* for loop */
    if (str_ieq(t.s, "for")) {
      parse_for_block(ps, out);
      continue;
    }

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

    /* macro call */
    macro_t *m = macro_find(&ps->macros, t.s);
    if (m) {
      parse_macro_call(ps, out, m);
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

      if (is_ptr_lit_word(t.s) && ((imm % 32u) != 0u)) {
        fprintf(stderr,
                "forth0c: %s:%u: WARN: %s immediate=0x%llx is not 32-bit aligned (bitaddr%%32!=0)\n",
                ps->lx->path, ps->lx->line, t.s, (unsigned long long)imm);
      }

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
  compile_from_buf(ps, path, buf, len, out);
  free(buf);
}
