/* f0c_for.inc — compile-time for/endfor */

static void compile_from_buf(pstate_t *ps, const char *path, char *buf, size_t len, FILE *out);

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

  unsigned depth = 0;
  for (;;) {
    token_t bt = p_take(ps);
    if (bt.k == TK_EOF) lex_die(ps->lx, "EOF inside for (missing endfor)");

    if (bt.k == TK_ID && str_ieq(bt.s, "for")) { depth++; macro_body_push(&body, &bt); continue; }

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
