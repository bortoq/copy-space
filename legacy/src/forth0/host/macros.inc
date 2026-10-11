/* forth0c_macros.inc — macro table + expansion helpers.
 *
 * Macro syntax handled by compiler:
 *   macro NAME(p1, p2, ...)
 *     ...body tokens...
 *   endmacro
 *
 * Call:
 *   NAME(expr1, expr2, ...)
 *
 * Expansion rule: identifiers matching param names inside body are replaced
 * with numeric literals (0x...) computed from call-site expressions.
 */

typedef struct {
  tk_kind_t k;
  char op;
  uint64_t num;
  char *s; /* for ID/STR */
} mtok_t;

typedef struct {
  char *name;
  char **params;
  size_t params_n;

  mtok_t *body;
  size_t body_n, body_cap;
} macro_t;

typedef struct {
  macro_t *v;
  size_t n, cap;
} macrotab_t;

static void macro_body_push(macro_t *m, const token_t *t) {
  if (m->body_n == m->body_cap) {
    size_t nc = m->body_cap ? m->body_cap * 2u : 64u;
    m->body = (mtok_t*)xrealloc(m->body, nc * sizeof(m->body[0]));
    m->body_cap = nc;
  }
  mtok_t *o = &m->body[m->body_n++];
  memset(o, 0, sizeof(*o));
  o->k = t->k;
  if (t->k == TK_OP) o->op = t->op;
  else if (t->k == TK_NUM) o->num = t->num;
  else if (t->k == TK_ID || t->k == TK_STR) o->s = xstrdup(t->s);
}

static void macro_free(macro_t *m) {
  if (!m) return;
  free(m->name);
  for (size_t i = 0; i < m->params_n; i++) free(m->params[i]);
  free(m->params);
  for (size_t i = 0; i < m->body_n; i++) free(m->body[i].s);
  free(m->body);
  memset(m, 0, sizeof(*m));
}

static macro_t *macro_find(macrotab_t *mt, const char *name) {
  for (size_t i = 0; i < mt->n; i++) {
    if (str_ieq(mt->v[i].name, name)) return &mt->v[i];
  }
  return NULL;
}

static macro_t *macro_put(macrotab_t *mt, const char *name) {
  macro_t *m = macro_find(mt, name);
  if (m) {
    macro_free(m);
    m->name = xstrdup(name);
    return m;
  }
  if (mt->n == mt->cap) {
    size_t nc = mt->cap ? mt->cap * 2u : 16u;
    mt->v = (macro_t*)xrealloc(mt->v, nc * sizeof(mt->v[0]));
    mt->cap = nc;
  }
  m = &mt->v[mt->n++];
  memset(m, 0, sizeof(*m));
  m->name = xstrdup(name);
  return m;
}

static void macro_free_all(macrotab_t *mt) {
  for (size_t i = 0; i < mt->n; i++) macro_free(&mt->v[i]);
  free(mt->v);
  memset(mt, 0, sizeof(*mt));
}

/* string builder */
typedef struct {
  char *p;
  size_t n, cap;
} sb_t;

static void sb_addc(sb_t *sb, char c) {
  if (sb->n + 1 >= sb->cap) {
    size_t nc = sb->cap ? sb->cap * 2u : 256u;
    sb->p = (char*)xrealloc(sb->p, nc);
    sb->cap = nc;
  }
  sb->p[sb->n++] = c;
  sb->p[sb->n] = 0;
}

static void sb_adds(sb_t *sb, const char *s) {
  while (*s) sb_addc(sb, *s++);
}

static void sb_add_u64_hex(sb_t *sb, uint64_t v) {
  char tmp[32];
  snprintf(tmp, sizeof(tmp), "0x%llx", (unsigned long long)v);
  sb_adds(sb, tmp);
}

static void sb_add_quoted(sb_t *sb, const char *s) {
  sb_addc(sb, '"');
  for (; *s; s++) {
    char c = *s;
    if (c == '"' || c == '\\') { sb_addc(sb, '\\'); sb_addc(sb, c); }
    else if (c == '\n') { sb_adds(sb, "\\n"); }
    else if (c == '\t') { sb_adds(sb, "\\t"); }
    else sb_addc(sb, c);
  }
  sb_addc(sb, '"');
}

static int macro_param_index(const macro_t *m, const char *id) {
  for (size_t i = 0; i < m->params_n; i++) {
    if (str_ieq(m->params[i], id)) return (int)i;
  }
  return -1;
}

static char *macro_expand_text(const macro_t *m, const uint64_t *args) {
  sb_t sb;
  memset(&sb, 0, sizeof(sb));

  for (size_t i = 0; i < m->body_n; i++) {
    const mtok_t *t = &m->body[i];
    if (t->k == TK_ID) {
      int pi = macro_param_index(m, t->s);
      if (pi >= 0) sb_add_u64_hex(&sb, args[(size_t)pi]);
      else sb_adds(&sb, t->s);
      sb_addc(&sb, ' ');
    } else if (t->k == TK_NUM) {
      sb_add_u64_hex(&sb, t->num);
      sb_addc(&sb, ' ');
    } else if (t->k == TK_OP) {
      sb_addc(&sb, t->op);
      sb_addc(&sb, ' ');
    } else if (t->k == TK_STR) {
      sb_add_quoted(&sb, t->s ? t->s : "");
      sb_addc(&sb, ' ');
    }
  }

  if (!sb.p) sb.p = xstrdup("");
  return sb.p; /* caller frees */
}
