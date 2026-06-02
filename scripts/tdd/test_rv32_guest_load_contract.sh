#!/bin/sh
set -eu

TMPDIR="$(mktemp -d tmp/rv32_guest_load.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

cat > "$TMPDIR/guest_load_contract.c" <<'C'
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

  uint64_t src = vm.workspace_base + 512;
  const uint8_t p[8] = {0xde,0xad,0xbe,0xef,0x11,0x22,0x33,0x44};
  memcpy(&vm.space[src >> 3], p, sizeof p);

  /* valid load */
  if (ch_call(&vm, 7, src, 0, 64) != 0) return 3;
  if (vm_bit_get(&vm, vm.mmio.ch_err)) return 4;
  if (memcmp(&vm.space[G_MEM_BASE >> 3], p, sizeof p) != 0) return 5;

  /* valid offset load */
  if (ch_call(&vm, 7, src, 128, 64) != 0) return 6;
  if (vm_bit_get(&vm, vm.mmio.ch_err)) return 7;
  if (memcmp(&vm.space[(G_MEM_BASE >> 3) + 16], p, sizeof p) != 0) return 8;

  /* negative: destination out of bounds */
  uint64_t off_bad = vm.space_bits - G_MEM_BASE - 32;
  if (ch_call(&vm, 7, src, off_bad, 128) != 0) return 9;
  if (!vm_bit_get(&vm, vm.mmio.ch_err)) return 10;
  if (vm_read_uint(&vm, vm.mmio.ch_c, vm.n_bits) != 1) return 11; /* bounds */

  vm_free(&vm);
  puts("OK rv32 guest load contract");
  return 0;
}
C

cc -O2 -I src/vm -o "$TMPDIR/guest_load_contract" \
  "$TMPDIR/guest_load_contract.c" src/vm/space.c src/vm/bitcpy.c

"$TMPDIR/guest_load_contract"
