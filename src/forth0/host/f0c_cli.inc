/* f0c_cli.inc — CLI + image loading */

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
