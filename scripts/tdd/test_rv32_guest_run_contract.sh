#!/bin/sh
set -eu

TMPDIR="$(mktemp -d tmp/rv32_guest_run.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

cat > "$TMPDIR/guest_run_contract.c" <<'C'
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
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 2;

  uint64_t src = vm.workspace_base + 1024;
  vm.space[src >> 3] = 0xaa;
  vm.space[(src >> 3) + 1] = 0x55;

  /* must reject RUN before LOAD_CODE */
  if (ch_call(&vm, 8, 0, 0, 2) != 0) return 3;
  if (!vm_bit_get(&vm, vm.mmio.ch_err)) return 4;
  if (vm_read_uint(&vm, vm.mmio.ch_c, vm.n_bits) != 3) return 5; /* protocol */

  /* unsupported channel op must fail deterministically with protocol error */
  if (ch_call(&vm, 255, 0, 0, 0) != 0) return 6;
  if (!vm_bit_get(&vm, vm.mmio.ch_err)) return 7;
  if (vm_read_uint(&vm, vm.mmio.ch_c, vm.n_bits) != 3) return 8; /* protocol */

  /* load -> run */
  if (ch_call(&vm, 7, src, 0, 16) != 0) return 9;
  if (vm_bit_get(&vm, vm.mmio.ch_err)) return 10;
  if (ch_call(&vm, 8, 0, 0, 5) != 0) return 11;
  if (vm_bit_get(&vm, vm.mmio.ch_err)) return 12;
  if (!vm_bit_get(&vm, vm.mmio.wd_enable)) return 13;

  uint64_t t0 = vm.tick_counter;
  for (int i = 0; i < 3; i++) {
    if (vm_tick(&vm, stdin, stdout) == VM_ERR) return 14;
  }
  if (vm.tick_counter <= t0) return 15;

  /* status must be readable */
  if (ch_call(&vm, 6, 0, 0, 0) != 0) return 16;
  if (vm_bit_get(&vm, vm.mmio.ch_err)) return 17;

  /* step re-arms bounded execution */
  if (ch_call(&vm, 9, 0, 0, 1) != 0) return 18;
  if (vm_bit_get(&vm, vm.mmio.ch_err)) return 19;

  vm_free(&vm);
  puts("OK rv32 guest run contract");
  return 0;
}
C

cc -O2 -I src/vm -o "$TMPDIR/guest_run_contract" \
  "$TMPDIR/guest_run_contract.c" src/vm/space.c src/vm/bitcpy.c

"$TMPDIR/guest_run_contract"
