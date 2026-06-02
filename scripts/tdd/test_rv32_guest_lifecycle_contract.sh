#!/bin/sh
set -eu

TMPDIR="$(mktemp -d tmp/rv32_guest_lifecycle.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

cat > "$TMPDIR/lifecycle_check.c" <<'C'
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

  /* idle -> loaded via LOAD_CODE */
  uint64_t src = vm.workspace_base + 128;
  vm.space[src >> 3] = 0xCA;
  vm.space[(src >> 3) + 1] = 0xFE;
  if (ch_call(&vm, 7, src, 0, 16) != 0) return 3;
  if (vm_bit_get(&vm, vm.mmio.ch_err)) return 4;
  if (vm.space[G_MEM_BASE >> 3] != 0xCA || vm.space[(G_MEM_BASE >> 3) + 1] != 0xFE) return 5;

  /* loaded -> running via RUN (watchdog armed) */
  if (ch_call(&vm, 8, 0, 0, 3) != 0) return 6;
  if (!vm_bit_get(&vm, vm.mmio.wd_enable)) return 7;

  /* RUN progress -> stopped/fired */
  vm_rc_t r1 = vm_tick(&vm, stdin, stdout);
  vm_rc_t r2 = vm_tick(&vm, stdin, stdout);
  (void)r1; (void)r2;
  if (!vm_bit_get(&vm, vm.mmio.wd_fired) && !vm_bit_get(&vm, vm.mmio.halt)) return 8;

  /* STATUS must be readable and non-error VM tick */
  if (ch_call(&vm, 6, 0, 0, 0) != 0) return 9;
  if (vm_bit_get(&vm, vm.mmio.ch_err)) return 10;

  vm_free(&vm);
  puts("OK rv32 guest lifecycle contract");
  return 0;
}
C

cc -O2 -I src/vm -o "$TMPDIR/lifecycle_check" \
  "$TMPDIR/lifecycle_check.c" src/vm/space.c src/vm/bitcpy.c

"$TMPDIR/lifecycle_check"
