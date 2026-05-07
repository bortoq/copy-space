/* forth0c_expr.inc — expression parser (included into forth0c TU). */

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
