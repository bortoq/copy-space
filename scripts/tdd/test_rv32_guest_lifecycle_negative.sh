#!/bin/sh
set -eu

TMPDIR="$(mktemp -d tmp/rv32_guest_lifecycle_neg.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

cat > "$TMPDIR/lifecycle_neg_check.c" <<'C'
#include <stdio.h>
#include <stdint.h>
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
  const uint64_t CH_E_BOUNDS = 1ull;
  const uint64_t CH_E_PROTOCOL = 3ull;
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 2;

  /* RUN before LOAD_CODE must fail with protocol error */
  if (ch_call(&vm, 8, 0, 0, 2) != 0) return 3;
  if (!vm_bit_get(&vm, vm.mmio.ch_err)) return 4;
  if (vm_read_uint(&vm, vm.mmio.ch_c, vm.n_bits) != CH_E_PROTOCOL) return 5;

  /* LOAD_CODE out-of-bounds must fail with bounds error */
  uint64_t src = vm.workspace_base + 64;
  vm.space[src >> 3] = 0xAA;
  if (ch_call(&vm, 7, src, vm.space_bits, 8) != 0) return 6;
  if (!vm_bit_get(&vm, vm.mmio.ch_err)) return 7;
  if (vm_read_uint(&vm, vm.mmio.ch_c, vm.n_bits) != CH_E_BOUNDS) return 8;

  vm_free(&vm);
  puts("OK rv32 guest lifecycle negative");
  return 0;
}
C

cc -O2 -I src/vm -o "$TMPDIR/lifecycle_neg_check" \
  "$TMPDIR/lifecycle_neg_check.c" src/vm/space.c src/vm/bitcpy.c

"$TMPDIR/lifecycle_neg_check"
