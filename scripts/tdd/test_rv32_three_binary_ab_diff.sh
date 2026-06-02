#!/bin/sh
set -eu

TMPDIR="$(mktemp -d tmp/rv32_ab_diff.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

cat > "$TMPDIR/a.S" <<'S'
.section .text
.globl _start
_start:
  li x1, 0x11111111
  .word 0
S

cat > "$TMPDIR/b.S" <<'S'
.section .text
.globl _start
_start:
  li x1, 0x22222222
  .word 0
S

riscv-none-elf-as -march=rv32i -mabi=ilp32 -o "$TMPDIR/a.o" "$TMPDIR/a.S"
riscv-none-elf-ld -m elf32lriscv -Ttext=0x0 -o "$TMPDIR/a.elf" "$TMPDIR/a.o"
riscv-none-elf-objcopy -O binary "$TMPDIR/a.elf" "$TMPDIR/a.bin"

riscv-none-elf-as -march=rv32i -mabi=ilp32 -o "$TMPDIR/b.o" "$TMPDIR/b.S"
riscv-none-elf-ld -m elf32lriscv -Ttext=0x0 -o "$TMPDIR/b.elf" "$TMPDIR/b.o"
riscv-none-elf-objcopy -O binary "$TMPDIR/b.elf" "$TMPDIR/b.bin"

cat > "$TMPDIR/ab_diff_check.c" <<'C'
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

static int run_one(const char *bin, uint8_t *out, size_t out_n) {
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 2;
  size_t sz = 0; uint8_t *b = loadf(bin, &sz);
  if (!b) { vm_free(&vm); return 3; }
  uint64_t src = vm.workspace_base + 1024;
  if ((src >> 3) + sz + out_n + 1024 >= vm.space_bytes) { free(b); vm_free(&vm); return 4; }
  memcpy(&vm.space[src >> 3], b, sz);
  free(b);

  if (ch_call(&vm, 7, src, 0, (uint64_t)sz * 8u) != 0) { vm_free(&vm); return 5; }
  if (vm_bit_get(&vm, vm.mmio.ch_err)) { vm_free(&vm); return 6; }

  uint64_t dst = vm.workspace_base + 4096;
  memset(out, 0, out_n);
  if (ch_call(&vm, 11, 0, dst, (uint64_t)out_n * 8u) != 0) { vm_free(&vm); return 7; }
  if (vm_bit_get(&vm, vm.mmio.ch_err)) { vm_free(&vm); return 8; }
  memcpy(out, &vm.space[dst >> 3], out_n);
  vm_free(&vm);
  return 0;
}

int main(int argc, char **argv) {
  if (argc != 3) return 64;
  uint8_t a[32], b[32];
  int ra = run_one(argv[1], a, sizeof a); if (ra) return 10 + ra;
  int rb = run_one(argv[2], b, sizeof b); if (rb) return 30 + rb;
  if (memcmp(a, b, sizeof a) == 0) return 61;
  puts("OK rv32 three-binary ab diff");
  return 0;
}
C

cc -O2 -I src/vm -o "$TMPDIR/ab_diff_check" \
  "$TMPDIR/ab_diff_check.c" src/vm/space.c src/vm/bitcpy.c

"$TMPDIR/ab_diff_check" "$TMPDIR/a.bin" "$TMPDIR/b.bin"
