/* f0c_mac.inc — parse macro def/call (macro db/expand is in forth0c_macros.inc) */

static void compile_stream(pstate_t *ps, FILE *out);
static void compile_one_file(pstate_t *ps, const char *path, FILE *out);
static void compile_from_buf(pstate_t *ps, const char *path, char *buf, size_t len, FILE *out);

static void parse_macro_def(pstate_t *ps) {
  token_t name = p_take(ps);
  if (name.k != TK_ID) lex_die(ps->lx, "macro expects NAME");

  macro_t *m = macro_put(&ps->macros, name.s);

  token_t t = p_peek(ps);
  if (t.k == TK_OP && t.op == '(') {
    p_take(ps);
    token_t p = p_peek(ps);
    if (p.k == TK_OP && p.op == ')') {
      p_take(ps);
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
    p_take(ps);
    token_t p = p_peek(ps);
    if (p.k == TK_OP && p.op == ')') {
      p_take(ps);
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
