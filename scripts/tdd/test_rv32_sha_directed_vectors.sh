#!/bin/sh
set -eu

TMPDIR="$(mktemp -d tmp/rv32_sha_vectors.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

cat > "$TMPDIR/rv32_vectors.c" <<'C'
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "space.h"

static int ch_call(vm_t *vm, unsigned op, uint64_t a, uint64_t b, uint64_t c) {
  vm_write_uint(vm, vm->mmio.ch_op, 8, op);
  vm_write_uint(vm, vm->mmio.ch_a, vm->addr_bits, a);
  vm_write_uint(vm, vm->mmio.ch_b, vm->addr_bits, b);
  vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, c);
  vm_bit_set(vm, vm->mmio.ch_req, 1);
  return vm_tick(vm, stdin, stdout) == VM_ERR ? -1 : 0;
}

int main(void) {
  const uint64_t G_MEM_BASE = 0x002000ull;
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 2;

  /* directed vector 1: addi-class payload marker */
  uint64_t src1 = vm.workspace_base + 64;
  vm.space[src1 >> 3] = 0x13; /* addi opcode low byte marker */
  if (ch_call(&vm, 7, src1, 0, 8) != 0 || vm_bit_get(&vm, vm.mmio.ch_err)) return 3;
  if (vm.space[G_MEM_BASE >> 3] != 0x13) return 4;

  /* directed vector 2: lw/sw-class marker roundtrip */
  uint64_t src2 = vm.workspace_base + 128;
  vm.space[src2 >> 3] = 0x23; /* sw opcode low byte marker */
  if (ch_call(&vm, 7, src2, 8, 8) != 0 || vm_bit_get(&vm, vm.mmio.ch_err)) return 5;
  uint64_t dst2 = vm.workspace_base + 256;
  if (ch_call(&vm, 11, 8, dst2, 8) != 0 || vm_bit_get(&vm, vm.mmio.ch_err)) return 6;
  if (vm.space[dst2 >> 3] != 0x23) return 7;

  /* directed vector 3: beq/bne-class control via lifecycle (run/step) */
  if (ch_call(&vm, 8, 0, 0, 2) != 0 || vm_bit_get(&vm, vm.mmio.ch_err)) return 8;
  if (ch_call(&vm, 9, 0, 0, 1) != 0 || vm_bit_get(&vm, vm.mmio.ch_err)) return 9;

  vm_free(&vm);
  puts("OK rv32 sha directed vectors");
  return 0;
}
C

cc -O2 -I src/vm -o "$TMPDIR/rv32_vectors" \
  "$TMPDIR/rv32_vectors.c" src/vm/space.c src/vm/bitcpy.c

"$TMPDIR/rv32_vectors"
