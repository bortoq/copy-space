// space.c — run a space.bin image on Copy-Space VM, optionally dump memory after run
#include "space.h"
#include <inttypes.h>
#include <stdlib.h>
#include <string.h>

static void usage(const char *a0) {
  fprintf(stderr,
    "usage: %s --image space.bin [--life N] [--dump after.bin]\n"
    "  --image        path to full memory image\n"
    "  --life         max ticks to run (default: 1e6)\n"
    "  --dump         dump full vm.space after run to a file\n",
    a0);
}

static int load_image(vm_t *vm, const char *path) {
  FILE *f = fopen(path, "rb");
  if (!f) { perror("fopen(image)"); return -1; }

  if (fseek(f, 0, SEEK_END) != 0) { perror("fseek"); fclose(f); return -1; }
  long sz = ftell(f);
  if (sz < 0) { perror("ftell"); fclose(f); return -1; }
  rewind(f);

  if ((size_t)sz != vm->space_bytes) {
    fprintf(stderr, "image size mismatch: file=%ld bytes, expected=%zu bytes\n",
            sz, vm->space_bytes);
    fclose(f);
    return -1;
  }

  size_t got = fread(vm->space, 1, vm->space_bytes, f);
  if (got != vm->space_bytes) {
    perror("fread(image)");
    fclose(f);
    return -1;
  }
  fclose(f);
  return 0;
}

static int dump_space(const vm_t *vm, const char *path) {
  FILE *f = fopen(path, "wb");
  if (!f) { perror("fopen(dump)"); return -1; }
  if (fwrite(vm->space, 1, vm->space_bytes, f) != vm->space_bytes) {
    perror("fwrite(dump)");
    fclose(f);
    return -1;
  }
  fclose(f);
  return 0;
}

int main(int argc, char **argv) {
  const char *image_path = NULL;
  const char *dump_path = NULL;

  uint64_t life = 1000000ull;

  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--image") && i + 1 < argc) image_path = argv[++i];
    else if (!strcmp(argv[i], "--dump") && i + 1 < argc) dump_path = argv[++i];
    else if (!strcmp(argv[i], "--life") && i + 1 < argc) life = strtoull(argv[++i], NULL, 0);
    else { usage(argv[0]); return 2; }
  }

  if (!image_path) { usage(argv[0]); return 2; }

  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) {
    fprintf(stderr, "vm_init failed\n");
    return 1;
  }

  if (load_image(&vm, image_path) != 0) {
    vm_free(&vm);
    return 1;
  }

  vm_rc_t rc = VM_OK;
  while (life--) {
    rc = vm_tick(&vm, stdin, stdout);
    if (rc != VM_OK) break;
  }

  if (dump_path) {
    if (dump_space(&vm, dump_path) != 0) {
      fprintf(stderr, "warning: failed to dump space to %s\n", dump_path);
    } else {
      fprintf(stderr, "dumped space to %s\n", dump_path);
    }
  }

  if (rc == VM_HALT) {
    fprintf(stderr, "VM halted by MMIO.HALT (ticks=%" PRIu64 ")\n", vm.tick_counter);
    vm_free(&vm);
    return 0;
  }
  if (rc == VM_OK) {
    fprintf(stderr, "VM finished (life exhausted, ticks=%" PRIu64 ")\n", vm.tick_counter);
    vm_free(&vm);
    return 0;
  }

  fprintf(stderr, "VM error (ticks=%" PRIu64 ")\n", vm.tick_counter);
  vm_free(&vm);
  return 1;
}
