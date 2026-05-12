// mkbench_bulkcopy.c
// Build a benchmark image that runs one large copy each VM tick (no HALT).
// Intended to measure vmrep avg bits/tick in steady-state.
//
// usage:
//   mkbench_bulkcopy --image base.bin --out bench.bin [--space-bytes N] [--processor-n N]
//                   [--len-bytes N] [--pad-bytes N]
//
// default: space-bytes=524288, processor-n=64, len-bytes=65536, pad-bytes=4096

#include "space.h"
#include "diag/vmrep_attach.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <inttypes.h>

static uint64_t parse_u64(const char *s) {
  char *e = NULL;
  unsigned long long v = strtoull(s, &e, 0);
  if (!s || !*s || !e || e == s) {
    fprintf(stderr, "bad number: '%s'\n", s ? s : "(null)");
    exit(2);
  }
  return (uint64_t)v;
}

static void die(const char *msg) {
  fprintf(stderr, "ERROR: %s\n", msg);
  exit(1);
}

static void read_file_into(uint8_t *dst, size_t cap, const char *path) {
  FILE *f = fopen(path, "rb");
  if (!f) die("cannot open input image");

  size_t got = fread(dst, 1, cap, f);
  if (ferror(f)) die("read error");
  fclose(f);

  // If image shorter than cap: rest stays as-is (caller should have zeroed).
  (void)got;
}

static void write_file(const uint8_t *src, size_t n, const char *path) {
  FILE *f = fopen(path, "wb");
  if (!f) die("cannot open output");
  size_t put = fwrite(src, 1, n, f);
  if (put != n) die("write error");
  fclose(f);
}

static bitaddr_t align_up_bits(bitaddr_t x, bitaddr_t a_bits) {
  if (a_bits == 0) return x;
  bitaddr_t m = a_bits - 1;
  return (x + m) & ~m;
}

int main(int argc, char **argv) {
  const char *in_path = NULL;
  const char *out_path = NULL;

  size_t space_bytes = 524288;
  unsigned processor_n = 64;
  size_t len_bytes = 65536;
  size_t pad_bytes = 4096;

  for (int i = 1; i < argc; i++) {
    if (strcmp(argv[i], "--image") == 0 && i + 1 < argc) { in_path = argv[++i]; continue; }
    if (strcmp(argv[i], "--out") == 0 && i + 1 < argc) { out_path = argv[++i]; continue; }
    if (strcmp(argv[i], "--space-bytes") == 0 && i + 1 < argc) { space_bytes = (size_t)parse_u64(argv[++i]); continue; }
    if (strcmp(argv[i], "--processor-n") == 0 && i + 1 < argc) { processor_n = (unsigned)parse_u64(argv[++i]); continue; }
    if (strcmp(argv[i], "--len-bytes") == 0 && i + 1 < argc) { len_bytes = (size_t)parse_u64(argv[++i]); continue; }
    if (strcmp(argv[i], "--pad-bytes") == 0 && i + 1 < argc) { pad_bytes = (size_t)parse_u64(argv[++i]); continue; }

    fprintf(stderr, "usage: %s --image base.bin --out bench.bin [--space-bytes N] [--processor-n N] [--len-bytes N] [--pad-bytes N]\n", argv[0]);
    return 2;
  }

  if (!in_path) die("--image required");
  if (!out_path) die("--out required");

  vm_t vm;
  if (vm_init(&vm, space_bytes, processor_n) != 0) die("vm_init failed");
  vmrep_attach(&vm);

  // zeroed space
  memset(vm.space, 0, vm.space_bytes);
  read_file_into(vm.space, vm.space_bytes, in_path);

  // clear processor: NOPs
  for (unsigned i = 0; i < vm.processor_n; i++) {
    vm_write_inst(&vm, vm_proc_slot_ip(&vm, i), (vm_inst_t){0,0,0});
  }

  // choose src/dst in workspace region
  bitaddr_t ws = vm.workspace_base;         // bitaddr
  bitaddr_t pad_bits = (bitaddr_t)pad_bytes * 8u;
  bitaddr_t len_bits = (bitaddr_t)len_bytes * 8u;

  // byte align (8 bits) is required by bitcpy impl; also nice to keep
  bitaddr_t src = align_up_bits(ws + pad_bits, 8);
  bitaddr_t dst = align_up_bits(src + len_bits + pad_bits, 8);

  if (src + len_bits > vm.space_bits) die("src range out of space");
  if (dst + len_bits > vm.space_bits) die("dst range out of space");

  size_t src_b = (size_t)(src >> 3);
  size_t dst_b = (size_t)(dst >> 3);

  // init pattern in src, clear dst
  for (size_t i = 0; i < len_bytes; i++) {
    vm.space[src_b + i] = (uint8_t)(i & 0xFFu);
  }
  memset(&vm.space[dst_b], 0, len_bytes);

  // slot0: one huge copy each tick
  vm_inst_t ins = {
    .n   = (uint64_t)len_bits,
    .dst = (uint64_t)dst,
    .src = (uint64_t)src
  };
  vm_write_inst(&vm, vm_proc_slot_ip(&vm, 0), ins);

  fprintf(stderr, "mkbench_bulkcopy: space_bytes=%zu processor_n=%u\n", space_bytes, processor_n);
  fprintf(stderr, "mkbench_bulkcopy: workspace_base(bit)=%" PRIu64 "\n", (uint64_t)ws);
  fprintf(stderr, "mkbench_bulkcopy: src(byte)=%zu dst(byte)=%zu len_bytes=%zu\n", src_b, dst_b, len_bytes);

  write_file(vm.space, vm.space_bytes, out_path);
  vm_free(&vm);
  return 0;
}
