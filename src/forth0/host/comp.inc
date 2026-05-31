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
  bitaddr_t saved_page_addr = ps->page_addr;
  unsigned saved_page_slot = ps->page_slot;
  int saved_if_depth = ps->if_depth;
  int saved_if_stack[IF_STACK_MAX];
  if (saved_if_depth >= 0)
    memcpy(saved_if_stack, ps->if_stack, (size_t)(saved_if_depth + 1) * sizeof(int));

  ps->lx = &lx;
  ps->have = 0;
  /* Do NOT inherit page/if state into included/macro context — reset */
  ps->page_addr = 0;
  ps->page_slot = 0;
  ps->if_depth = -1;

  compile_stream(ps, out);

  ps->lx = saved_lx;
  ps->have = saved_have;
  ps->cur = saved_cur;
  ps->page_addr = saved_page_addr;
  ps->page_slot = saved_page_slot;
  ps->if_depth = saved_if_depth;
  if (saved_if_depth >= 0)
    memcpy(ps->if_stack, saved_if_stack, (size_t)(saved_if_depth + 1) * sizeof(int));
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

/* -------------------- if/else/endif -------------------- */

/* Returns 1 if any ancestor if-frame is in skip mode */
static int if_is_skipping(pstate_t *ps) {
  for (int i = 0; i <= ps->if_depth; i++)
    if (!ps->if_stack[i]) return 1;
  return 0;
}

/* -------------------- while/endwhile -------------------- */

static void parse_while_block(pstate_t *ps, FILE *out) {
  /* Save lexer position for condition re-evaluation */
  size_t cond_i = ps->lx->i;
  unsigned cond_line = ps->lx->line;

  uint64_t cond = parse_expr(ps);

  /* Capture body tokens (same technique as for.inc) */
  macro_t body;
  memset(&body, 0, sizeof(body));
  body.name = xstrdup("while_body");
  unsigned depth = 0;

  for (;;) {
    token_t bt = p_take(ps);
    if (bt.k == TK_EOF) lex_die(ps->lx, "EOF inside while (missing endwhile)");
    if (bt.k == TK_ID && str_ieq(bt.s, "while")) { depth++; macro_body_push(&body, &bt); continue; }
    if (bt.k == TK_ID && str_ieq(bt.s, "endwhile")) {
      if (depth == 0) break;
      depth--;
      macro_body_push(&body, &bt);
      continue;
    }
    macro_body_push(&body, &bt);
  }

  /* Iterate: re-evaluate condition each time */
  while (cond != 0) {
    uint64_t arg = 0;
    char *txt = macro_expand_text(&body, &arg);
    compile_from_buf(ps, "while", txt, strlen(txt), out);
    free(txt);

    /* Re-evaluate condition — restore lexer to beginning of condition */
    ps->lx->i = cond_i;
    ps->lx->line = cond_line;
    ps->have = 0;
    cond = parse_expr(ps);
  }

  macro_free(&body);
}

/* -------------------- page/endpage -------------------- */

static void parse_page_def(pstate_t *ps, FILE *out) {
  (void)out; /* only sets parser state */
  /* parse slot number or name */
  token_t t = p_peek(ps);
  uint64_t slot_val = 0;
  if (t.k == TK_ID) {
    /* Look up as const first, else error */
    p_take(ps);
    uint64_t cv = 0;
    if (const_get(&ps->consts, t.s, &cv)) {
      slot_val = cv;
    } else {
      fprintf(stderr, "forth0c: %s:%u: expected slot number or const after page\n",
              ps->lx->path, ps->lx->line);
      exit(1);
    }
  } else {
    slot_val = parse_expr(ps);
  }

  uint64_t step = 0, words_base = 0;
  const_get(&ps->consts, "STEP", &step);
  const_get(&ps->consts, "WORDS_BASE", &words_base);

  ps->page_addr = words_base + slot_val * step;
  ps->page_slot = 0;
}

/* -------------------- main loop -------------------- */

static void compile_stream(pstate_t *ps, FILE *out) {
  for (;;) {
    token_t t = p_peek(ps);
    if (t.k == TK_EOF) return;
    if (t.k != TK_ID) lex_die(ps->lx, "expected word/directive");
    t = p_take(ps);

    /* ----- macro ----- */
    if (str_ieq(t.s, "macro")) { parse_macro_def(ps); continue; }

    /* ----- for/while ----- */
    if (str_ieq(t.s, "for"))   { parse_for_block(ps, out); continue; }
    if (str_ieq(t.s, "while")) { parse_while_block(ps, out); continue; }

    /* ----- if/else/endif (compile-time conditional) ----- */
    if (str_ieq(t.s, "if")) {
      uint64_t cond = parse_expr(ps);
      ps->if_depth++;
      if (ps->if_depth >= IF_STACK_MAX) lex_die(ps->lx, "if nesting too deep");
      ps->if_stack[ps->if_depth] = (cond != 0) ? 1 : 0;
      continue;
    }
    if (str_ieq(t.s, "else")) {
      if (ps->if_depth < 0) lex_die(ps->lx, "else without if");
      ps->if_stack[ps->if_depth] = !ps->if_stack[ps->if_depth];
      continue;
    }
    if (str_ieq(t.s, "endif")) {
      if (ps->if_depth < 0) lex_die(ps->lx, "endif without if");
      ps->if_depth--;
      continue;
    }

    /* ----- skip mode: ignore everything except if/else/endif/while/for/macro/endmacro ----- */
    if (if_is_skipping(ps)) {
      /* Nested flow-control markers inside skipped region — still track nesting */
      if (str_ieq(t.s, "if")) {
        ps->if_depth++;
        if (ps->if_depth >= IF_STACK_MAX) lex_die(ps->lx, "if nesting too deep");
        ps->if_stack[ps->if_depth] = 0; /* inherited skip */
      } else if (str_ieq(t.s, "else")) {
        if (ps->if_depth < 0) lex_die(ps->lx, "else without if");
      } else if (str_ieq(t.s, "endif")) {
        if (ps->if_depth < 0) lex_die(ps->lx, "endif without if");
        ps->if_depth--;
      }
      continue;
    }

    /* ----- on/off toggles ----- */
    if (str_ieq(t.s, "on")) {
      token_t what = p_take(ps);
      if (what.k != TK_ID) lex_die(ps->lx, "on expects a toggle name");
      if (str_ieq(what.s, "strict") || str_ieq(what.s, "strict_align32")) {
        ps->flags |= 1u;
        /* set env for existing strict check */
        setenv("F0C_STRICT_ALIGN32", "1", 1);
      } else {
        fprintf(stderr, "forth0c: %s:%u: unknown toggle: %s\n", ps->lx->path, ps->lx->line, what.s);
        exit(1);
      }
      continue;
    }
    if (str_ieq(t.s, "off")) {
      token_t what = p_take(ps);
      if (what.k != TK_ID) lex_die(ps->lx, "off expects a toggle name");
      if (str_ieq(what.s, "strict") || str_ieq(what.s, "strict_align32")) {
        ps->flags &= ~1u;
        setenv("F0C_STRICT_ALIGN32", "0", 1);
      } else {
        fprintf(stderr, "forth0c: %s:%u: unknown toggle: %s\n", ps->lx->path, ps->lx->line, what.s);
        exit(1);
      }
      continue;
    }

    /* ----- page/endpage ----- */
    if (str_ieq(t.s, "page")) {
      parse_page_def(ps, out);
      continue;
    }
    if (str_ieq(t.s, "endpage")) {
      if (ps->page_addr == 0) lex_die(ps->lx, "endpage without page");
      ps->page_addr = 0;
      ps->page_slot = 0;
      continue;
    }

    /* ----- instr (inside page block) ----- */
    if (str_ieq(t.s, "instr")) {
      if (ps->page_addr == 0) lex_die(ps->lx, "instr outside page block");
      do_instr(ps, out, ps->page_addr, ps->page_slot);
      ps->page_slot++;
      continue;
    }

    /* ----- word_page ----- */
    if (str_ieq(t.s, "word_page")) {
      token_t name = p_take(ps);
      if (name.k != TK_ID) lex_die(ps->lx, "word_page expects NAME");
      uint64_t slot_val = parse_expr(ps);

      /* Register as a guest ART symbol (maps name → direct bitaddr) */
      uint64_t step = 0, words_base = 0;
      const_get(&ps->consts, "STEP", &step);
      const_get(&ps->consts, "WORDS_BASE", &words_base);
      bitaddr_t waddr = words_base + slot_val * step;
      const_set(&ps->consts, name.s, (uint64_t)waddr);
      continue;
    }

    /* ----- include / const / emit / copybits / setbit / setbyte / set24 ----- */
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

    /* ----- macro call ----- */
    macro_t *m = macro_find(&ps->macros, t.s);
    if (m) { parse_macro_call(ps, out, m); continue; }

    /* ----- ART word ----- */
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
