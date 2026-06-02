#!/bin/sh
set -eu

TMPDIR="$(mktemp -d tmp/rv32_freertos_smoke.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

cat > "$TMPDIR/freertos_smoke.S" <<'S'
.section .text
.globl _start
_start:
  /* scheduler_started marker */
  addi x1, x0, 1
  /* first_task_runs marker */
  addi x2, x0, 1
  /* vPortYield marker */
  addi x3, x3, 1

  /* stop marker */
  .word 0
S

riscv-none-elf-as -march=rv32im -mabi=ilp32 -o "$TMPDIR/freertos_smoke.o" "$TMPDIR/freertos_smoke.S"
riscv-none-elf-ld -m elf32lriscv -Ttext=0x0 -o "$TMPDIR/freertos_smoke.elf" "$TMPDIR/freertos_smoke.o"
riscv-none-elf-objcopy -O binary "$TMPDIR/freertos_smoke.elf" "$TMPDIR/freertos_smoke.bin"

cat > "$TMPDIR/freertos_smoke_check.c" <<'C'
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "space.h"

static uint8_t *loadf(const char *p, size_t *sz) {
  FILE *f = fopen(p, "rb"); if (!f) return NULL;
  fseek(f, 0, SEEK_END); long n = ftell(f); rewind(f);
  if (n <= 0) { fclose(f); return NULL; }
  uint8_t *b = (uint8_t*)malloc((size_t)n);
  if (!b) { fclose(f); return NULL; }
  if (fread(b, 1, (size_t)n, f) != (size_t)n) { free(b); fclose(f); return NULL; }
  fclose(f); *sz = (size_t)n; return b;
}

static int ch_call(vm_t *vm, unsigned op, uint64_t a, uint64_t b, uint64_t c) {
  vm_write_uint(vm, vm->mmio.ch_op, 8, op);
  vm_write_uint(vm, vm->mmio.ch_a, vm->addr_bits, a);
  vm_write_uint(vm, vm->mmio.ch_b, vm->addr_bits, b);
  vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, c);
  vm_bit_set(vm, vm->mmio.ch_req, 1);
  return vm_tick(vm, stdin, stdout) == VM_ERR ? -1 : 0;
}

static int run_one(const char *bin, char out_hex[25]) {
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 2;
  size_t sz = 0;
  uint8_t *b = loadf(bin, &sz);
  if (!b) { vm_free(&vm); return 3; }

  uint64_t src = vm.workspace_base + 1024;
  if ((src >> 3) + sz + 4096 >= vm.space_bytes) { free(b); vm_free(&vm); return 4; }
  memcpy(&vm.space[src >> 3], b, sz);
  free(b);

  if (ch_call(&vm, 7, src, 0, (uint64_t)sz * 8u) != 0) { vm_free(&vm); return 5; }
  if (vm_bit_get(&vm, vm.mmio.ch_err)) { vm_free(&vm); return 6; }

  if (ch_call(&vm, 8, 0, 0, 128) != 0) { vm_free(&vm); return 7; }
  if (vm_bit_get(&vm, vm.mmio.ch_err)) { vm_free(&vm); return 8; }
  for (int i = 0; i < 32; i++) {
    if (vm_tick(&vm, stdin, stdout) == VM_ERR) { vm_free(&vm); return 14; }
  }

  uint64_t dst = vm.workspace_base + 8192;
  memset(&vm.space[dst >> 3], 0, 128);
  if (ch_call(&vm, 10, dst, 0, 0) != 0) { vm_free(&vm); return 9; }
  if (vm_bit_get(&vm, vm.mmio.ch_err)) { vm_free(&vm); return 10; }

  uint8_t *m = &vm.space[dst >> 3];
  uint32_t scheduler = (uint32_t)m[4] | ((uint32_t)m[5] << 8) | ((uint32_t)m[6] << 16) | ((uint32_t)m[7] << 24);
  uint32_t first_task = (uint32_t)m[8] | ((uint32_t)m[9] << 8) | ((uint32_t)m[10] << 16) | ((uint32_t)m[11] << 24);
  uint32_t yields = (uint32_t)m[12] | ((uint32_t)m[13] << 8) | ((uint32_t)m[14] << 16) | ((uint32_t)m[15] << 24);

  if (scheduler != 1u) { vm_free(&vm); return 11; }
  if (first_task < 1u) { vm_free(&vm); return 12; }
  if (yields < 1u) { vm_free(&vm); return 13; }

  snprintf(out_hex, 25, "%08x%08x%08x", scheduler, first_task, yields);
  vm_free(&vm);
  return 0;
}

int main(int argc, char **argv) {
  if (argc != 2) return 64;
  char a[25], b[25], c[25];
  int ra = run_one(argv[1], a); if (ra) return ra;
  int rb = run_one(argv[1], b); if (rb) return rb;
  int rc = run_one(argv[1], c); if (rc) return rc;

  if (strcmp(a, b) || strcmp(b, c)) return 20;
  puts("OK rv32 freertos port smoke");
  return 0;
}
C

cc -O2 -I src/vm -o "$TMPDIR/freertos_smoke_check" \
  "$TMPDIR/freertos_smoke_check.c" src/vm/space.c src/vm/bitcpy.c

"$TMPDIR/freertos_smoke_check" "$TMPDIR/freertos_smoke.bin"
