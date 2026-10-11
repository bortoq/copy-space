/*
 * ASSEMPLER
 *
 * copyright 2022-12-21, dmitri bortoq, mit license
 * SPDX-License-Identifier: MIT
 */
#include "core.h"
#include <ctype.h>
#include <errno.h>

enum {
  MAX_LINE = 1024,
  MAX_SYMBOLS = 2048,
};

typedef struct {
  char name[64];
  unsigned long value;
} symbol;

size processor[PROCESSOR_N][INSTRUCTION_FIELDS];
char space[VM_SPACE_BYTES * 8 / CHAR_BIT];
const size o[] = {0, N_SIZE, N_SIZE + ADDRESS_SIZE};
const size s[] = {N_SIZE, ADDRESS_SIZE, ADDRESS_SIZE};

static symbol symbols[MAX_SYMBOLS];
static size_t symbol_n = 0;

static void bit_set_local(unsigned char *p, size_t bitpos, unsigned v)
{
  unsigned char *b = &p[bitpos >> 3];
  unsigned shift = 7u - (unsigned)(bitpos & 7u);
  unsigned char mask = (unsigned char)(1u << shift);
  if(v) *b |= mask;
  else  *b &= (unsigned char)~mask;
}

static void write_field_bits(size_t dst_bit, size value, size width)
{
  size i;
  for(i = 0; i < width; ++i)
    bit_set_local((unsigned char*)space, dst_bit + i, (unsigned)((value >> i) & 1u));
}

static void fail(const char *path, size_t line_no, const char *msg)
{
  if(path)
    fprintf(stderr, "%s:%lu: %s\n", path, (unsigned long)line_no, msg);
  else
    fprintf(stderr, "%s\n", msg);
  exit(1);
}

static int is_name_start(int c)
{
  return isalpha(c) || c == '_';
}

static void skip_spaces(char **p)
{
  while(**p && isspace((unsigned char)**p))
    ++*p;
}

static void strip_comment(char *line)
{
  char *comment = strchr(line, ';');
  if(comment)
    *comment = '\0';
}

static int read_token(char **p, char *buf, size_t buf_size)
{
  size_t i = 0;
  skip_spaces(p);
  if(!**p)
    return 0;
  if(**p == '"')
  {
    ++*p;
    while(**p && **p != '"' && i + 1 < buf_size)
      buf[i++] = *(*p)++;
    if(**p == '"')
      ++*p;
  }
  else
  {
    while(**p && !isspace((unsigned char)**p) && i + 1 < buf_size)
      buf[i++] = *(*p)++;
  }
  buf[i] = '\0';
  return i != 0;
}

static symbol *find_symbol(const char *name)
{
  size_t i;
  for(i = 0; i < symbol_n; ++i)
    if(strcmp(symbols[i].name, name) == 0)
      return &symbols[i];
  return NULL;
}

static void define_symbol(const char *name, unsigned long value)
{
  symbol *s = find_symbol(name);
  if(s)
  {
    s->value = value;
    return;
  }
  if(symbol_n >= MAX_SYMBOLS)
    fail(NULL, 0, "symbol table overflow");
  strncpy(symbols[symbol_n].name, name, sizeof symbols[symbol_n].name - 1);
  symbols[symbol_n].name[sizeof symbols[symbol_n].name - 1] = '\0';
  symbols[symbol_n].value = value;
  ++symbol_n;
}

static unsigned long parse_number(const char *token)
{
  char *end = NULL;
  unsigned long value;
  errno = 0;
  if(token[0] == '0' && token[1] == 'b')
  {
    value = 0;
    token += 2;
    while(*token == '0' || *token == '1')
    {
      value = (value << 1) | (unsigned long)(*token - '0');
      ++token;
    }
    if(*token != '\0')
      fail(NULL, 0, "invalid binary literal");
  }
  else
  {
    value = strtoul(token, &end, 0);
    if(errno || !end || *end != '\0')
      fail(NULL, 0, "invalid numeric literal");
  }
  return value;
}

static unsigned long atom_value(const char *token)
{
  symbol *s;
  if(isdigit((unsigned char)token[0]))
    return parse_number(token);
  if(token[0] == '0' && (token[1] == 'x' || token[1] == 'b'))
    return parse_number(token);
  s = find_symbol(token);
  if(!s)
    fail(NULL, 0, "unknown symbol");
  return s->value;
}

static unsigned long eval_expr(const char *expr)
{
  char atom[128];
  const char *p = expr;
  unsigned long value;
  size_t i = 0;
  if(!*p)
    fail(NULL, 0, "empty expression");
  while(*p && *p != '+' && *p != '-')
  {
    if(i + 1 >= sizeof atom)
      fail(NULL, 0, "expression too long");
    atom[i++] = *p++;
  }
  atom[i] = '\0';
  value = atom_value(atom);
  while(*p)
  {
    int op = *p++;
    i = 0;
    if(!*p)
      fail(NULL, 0, "truncated expression");
    while(*p && *p != '+' && *p != '-')
    {
      if(i + 1 >= sizeof atom)
        fail(NULL, 0, "expression too long");
      atom[i++] = *p++;
    }
    atom[i] = '\0';
    if(op == '+')
      value = (size)(value + atom_value(atom));
    else
      value = (size)(value - atom_value(atom));
  }
  return value;
}

static void init_predefined_symbols(void)
{
  define_symbol("SPACE_SIZE", SPACE_SIZE);
  define_symbol("PROCESSOR_N", PROCESSOR_N);
  define_symbol("PROCESSOR_START", PROCESSOR_START);
  define_symbol("INSTRUCTION_SIZE", INSTRUCTION_SIZE);
  define_symbol("N_SIZE", N_SIZE);
  define_symbol("ADDRESS_SIZE", ADDRESS_SIZE);
  define_symbol("PROCESSOR_BITS", PROCESSOR_BITS);
  define_symbol("CORE_LAYER_BITS", CORE_LAYER_BITS);
  define_symbol("CORE_INPUT_BITS", CORE_INPUT_BITS);
  define_symbol("CORE_BUFFER_START", CORE_BUFFER_START);
  define_symbol("CORE_RESTART_START", CORE_RESTART_START);
}

static void write_code(size_t n)
{
  size i = (size)n;
  write_field_bits(INSTRUCTION_SIZE * i + o[0], processor[i][0], s[0]);
  write_field_bits(INSTRUCTION_SIZE * i + o[1], processor[i][1], s[1]);
  write_field_bits(INSTRUCTION_SIZE * i + o[2], processor[i][2], s[2]);
}

static void flush_space(size_t i)
{
  fwrite(space, (INSTRUCTION_SIZE * i + CHAR_BIT - 1) / CHAR_BIT, 1, stdout);
}

static void compile_file(FILE *in, const char *path, size_t *instruction_n);

static FILE *open_include(const char *base_path, const char *include_name, char *resolved, size_t resolved_size)
{
  const char *slash = strrchr(base_path, '/');
  FILE *f = NULL;
  if(slash)
  {
    size_t dir_len = (size_t)(slash - base_path + 1);
    if(dir_len + strlen(include_name) + 1 < resolved_size)
    {
      memcpy(resolved, base_path, dir_len);
      strcpy(resolved + dir_len, include_name);
      f = fopen(resolved, "r");
      if(f)
        return f;
    }
  }
  strncpy(resolved, include_name, resolved_size - 1);
  resolved[resolved_size - 1] = '\0';
  return fopen(resolved, "r");
}

static void emit_instruction(size_t *instruction_n, size a, size b, size c,
                             const char *path, size_t line_no)
{
  if(*instruction_n >= PROCESSOR_N)
    fail(path, line_no, "too many instructions (PROCESSOR_N limit)");
  size i = (size)*instruction_n;
  processor[i][0] = a;
  processor[i][1] = b;
  processor[i][2] = c;
  write_code(*instruction_n);
  ++*instruction_n;
}

static void compile_line(char *line, const char *path, size_t line_no, size_t *instruction_n)
{
  char *p = line;
  char t0[256], t1[256], t2[256], t3[256], extra[256];
  strip_comment(line);
  if(!read_token(&p, t0, sizeof t0))
    return;
  if(strcmp(t0, "include") == 0)
  {
    char resolved[1024];
    FILE *f;
    if(!read_token(&p, t1, sizeof t1))
      fail(path, line_no, "missing include path");
    f = open_include(path, t1, resolved, sizeof resolved);
    if(!f)
      fail(path, line_no, "cannot open include file");
    compile_file(f, resolved, instruction_n);
    fclose(f);
    return;
  }
  if(strcmp(t0, "copy") == 0)
  {
    if(!read_token(&p, t1, sizeof t1) ||
       !read_token(&p, t2, sizeof t2) ||
       !read_token(&p, t3, sizeof t3))
      fail(path, line_no, "copy requires 3 arguments");
    if(read_token(&p, extra, sizeof extra))
      fail(path, line_no, "extra token after instruction");
    emit_instruction(instruction_n, (size)eval_expr(t1), (size)eval_expr(t2),
                     (size)eval_expr(t3), path, line_no);
    return;
  }
  if(!read_token(&p, t1, sizeof t1))
    fail(path, line_no, "missing token");
  if(!read_token(&p, t2, sizeof t2))
  {
    if(!is_name_start((unsigned char)t0[0]))
      fail(path, line_no, "invalid symbol name");
    define_symbol(t0, eval_expr(t1));
    return;
  }
  if(read_token(&p, extra, sizeof extra))
    fail(path, line_no, "extra token after instruction");
  emit_instruction(instruction_n, (size)eval_expr(t0), (size)eval_expr(t1),
                   (size)eval_expr(t2), path, line_no);
}

static void compile_file(FILE *in, const char *path, size_t *instruction_n)
{
  char line[MAX_LINE];
  size_t line_no = 0;
  while(fgets(line, sizeof line, in))
  {
    ++line_no;
    compile_line(line, path, line_no, instruction_n);
  }
}

int main()
{
  size_t n = 0;
  init_predefined_symbols();
  compile_file(stdin, "<stdin>", &n);
  flush_space(n);
  return 0;
}
