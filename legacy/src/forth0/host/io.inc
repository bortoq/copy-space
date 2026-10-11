/* io.inc — file + path helpers */

static char *read_file_all(const char *path, size_t *out_len) {
  FILE *f = fopen(path, "rb");
  if (!f) return NULL;
  if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return NULL; }
  long sz = ftell(f);
  if (sz < 0) { fclose(f); return NULL; }
  rewind(f);
  char *buf = (char*)malloc((size_t)sz + 1u);
  if (!buf) return NULL;
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
