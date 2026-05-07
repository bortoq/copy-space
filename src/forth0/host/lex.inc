/* forth0c_lex.inc — lexer (included into forth0c TU). */

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
  if (c=='+' || c=='-' || c=='*' || c=='/' || c=='(' || c==')' || c==',') {
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
