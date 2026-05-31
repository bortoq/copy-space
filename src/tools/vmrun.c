// vmrun.c — run a space.bin image on Copy-Space VM, optionally dump memory after run
#include "space.h"
#include "invariants.h"
#include "diag/vmrep_attach.h"
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>

static int env_enabled(const char *name) {
  const char *s = getenv(name);
  if (!s) return 0;
  if (!strcmp(s, "1")) return 1;
  if (!strcmp(s, "true")) return 1;
  if (!strcmp(s, "TRUE")) return 1;
  return 0;
}

static void usage(const char *a0) {
  fprintf(stderr,
    "usage: %s --image space.bin [--life N] [--space-bytes N] [--processor-n N] [--dump after.bin] [--trace-jsonl path]\n"
    "  --image        path to full memory image\n"
    "  --life         max ticks to run (default: 1e6)\n"
    "  --space-bytes  must match image build (default: VM_SPACE_BYTES)\n"
    "  --processor-n  must match image build (default: VM_PROCESSOR_N)\n"
    "  --dump         dump full vm.space after run to a file\n"
    "  --trace-jsonl  write per-tick copy trace as JSONL\n"
    "\n"
    "env:\n"
    "  COPYSPACE_VM_STRICT_ALIGN32=1  enforce 32-bit alignment for VAR_AP/VAR_BP/VAR_RP (std7_fixed)\n",
    a0);
}

typedef struct {
  FILE *f;
  uint64_t tick;
  int first;
} trace_ctx_t;

static void trace_tick_begin(void *user, size_t slots_cap) {
  (void)slots_cap;
  trace_ctx_t *t = (trace_ctx_t *)user;
  if (!t || !t->f) return;
  t->first = 1;
  fprintf(t->f, "{\"tick\":%" PRIu64 ",\"copies\":[", t->tick);
}

static void trace_note_copy(void *user, unsigned slot, uint64_t dst, uint64_t n, uint64_t src) {
  trace_ctx_t *t = (trace_ctx_t *)user;
  if (!t || !t->f) return;
  if (!t->first) fputc(',', t->f);
  t->first = 0;
  fprintf(t->f,
          "{\"slot\":%u,\"dst\":%" PRIu64 ",\"n\":%" PRIu64 ",\"src\":%" PRIu64 "}",
          slot, dst, n, src);
}

static void trace_tick_end(void *user) {
  trace_ctx_t *t = (trace_ctx_t *)user;
  if (!t || !t->f) return;
  fprintf(t->f, "]}\n");
  t->tick++;
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
  const char *trace_path = NULL;

  uint64_t life = 1000000ull;
  size_t space_bytes = VM_SPACE_BYTES;
  unsigned processor_n = VM_PROCESSOR_N;

  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--image") && i + 1 < argc) image_path = argv[++i];
    else if (!strcmp(argv[i], "--dump") && i + 1 < argc) dump_path = argv[++i];
    else if (!strcmp(argv[i], "--trace-jsonl") && i + 1 < argc) trace_path = argv[++i];
    else if (!strcmp(argv[i], "--life") && i + 1 < argc) life = strtoull(argv[++i], NULL, 0);
    else if (!strcmp(argv[i], "--space-bytes") && i + 1 < argc) space_bytes = (size_t)strtoull(argv[++i], NULL, 0);
    else if (!strcmp(argv[i], "--processor-n") && i + 1 < argc) processor_n = (unsigned)strtoul(argv[++i], NULL, 0);
    else { usage(argv[0]); return 2; }
  }

  if (!image_path) { usage(argv[0]); return 2; }

  vm_t vm;
  if (vm_init(&vm, space_bytes, processor_n) != 0) {
    fprintf(stderr, "vm_init failed\n");
    return 1;
  }

  if (load_image(&vm, image_path) != 0) {
    vm_free(&vm);
    return 1;
  }

  vmrep_attach(&vm);

  trace_ctx_t trace = {0};
  if (trace_path) {
    trace.f = fopen(trace_path, "w");
    if (!trace.f) {
      perror("fopen(trace-jsonl)");
      vm_free(&vm);
      return 1;
    }
    vm.hooks.user = &trace;
    vm.hooks.tick_begin = trace_tick_begin;
    vm.hooks.note_copy = trace_note_copy;
    vm.hooks.tick_end = trace_tick_end;
  }

  vm.strict_align32 = env_enabled("COPYSPACE_VM_STRICT_ALIGN32");

  vm_rc_t rc = VM_OK;
  while (life--) {
    rc = vm_tick(&vm, stdin, stdout);
    if (rc != VM_OK) break;
    if (vm.strict_align32) {
      if (vm_invariants_strict_align32_check(&vm) != 0) { rc = VM_ERR; break; }
    }
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
    if (trace.f) fclose(trace.f);
    vm_free(&vm);
    return 0;
  }
  if (rc == VM_OK) {
    fprintf(stderr, "VM finished (life exhausted, ticks=%" PRIu64 ")\n", vm.tick_counter);
    if (trace.f) fclose(trace.f);
    vm_free(&vm);
    return 0;
  }

  fprintf(stderr, "VM error (ticks=%" PRIu64 ")\n", vm.tick_counter);
  if (trace.f) fclose(trace.f);
  vm_free(&vm);
  return 1;
}
