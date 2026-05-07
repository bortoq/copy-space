/* comp.inc — compilation core (stream/include/buf) */

static int strict_align32_enabled(void) {
  const char *s = getenv("F0C_STRICT_ALIGN32");
  return (s && *s && strcmp(s, "0") != 0);
}

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

static void compile_stream(pstate_t *ps, FILE *out) {
  for (;;) {
    token_t t = p_peek(ps);
    if (t.k == TK_EOF) return;
    if (t.k != TK_ID) lex_die(ps->lx, "expected word/directive");

    t = p_take(ps);

    if (str_ieq(t.s, "macro")) { parse_macro_def(ps); continue; }
    if (str_ieq(t.s, "for"))   { parse_for_block(ps, out); continue; }

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

    macro_t *m = macro_find(&ps->macros, t.s);
    if (m) { parse_macro_call(ps, out, m); continue; }

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
        if (strict_align32_enabled()) {
          fprintf(stderr,
                  "forth0c: %s:%u: ERROR: %s immediate=0x%llx is not 32-bit aligned (bitaddr%%32!=0)\n",
                  ps->lx->path, ps->lx->line, t.s, (unsigned long long)imm);
          exit(1);
        } else {
          fprintf(stderr,
                  "forth0c: %s:%u: WARN: %s immediate=0x%llx is not 32-bit aligned (bitaddr%%32!=0)\n",
                  ps->lx->path, ps->lx->line, t.s, (unsigned long long)imm);
        }
      }

      emit_u(ps->vm, out, imm);
    }
  }
}
