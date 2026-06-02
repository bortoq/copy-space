#!/bin/sh
set -eu

TMPDIR="$(mktemp -d tmp/rv32_runtime_abi_ops.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

cat > "$TMPDIR/abi_ops_check.c" <<'C'
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
  const uint64_t G_REG_BASE = 0x001200ull;
  const uint64_t G_MEM_BASE = 0x002000ull;
  const uint64_t CH_E_BOUNDS = 1ull;
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 2;

  /* seed source payload at workspace */
  uint64_t src = vm.workspace_base + 128;
  for (int i = 0; i < 4; i++) vm.space[(src >> 3) + i] = (uint8_t)(0xA0 + i);

  /* op7 LOAD_CODE: 32 bits from src -> G_MEM_BASE+0 */
  if (ch_call(&vm, 7, src, 0, 32) != 0) return 3;
  if (memcmp(&vm.space[G_MEM_BASE >> 3], &vm.space[src >> 3], 4) != 0) return 4;

  /* op11 READ_MEM: copy back to dst */
  uint64_t dst = vm.workspace_base + 256;
  memset(&vm.space[dst >> 3], 0, 4);
  if (ch_call(&vm, 11, 0, dst, 32) != 0) return 5;
  if (memcmp(&vm.space[dst >> 3], &vm.space[G_MEM_BASE >> 3], 4) != 0) return 6;

  /* op12 WRITE_MEM: overwrite mem from another source */
  uint64_t src2 = vm.workspace_base + 320;
  for (int i = 0; i < 4; i++) vm.space[(src2 >> 3) + i] = (uint8_t)(0xB0 + i);
  if (ch_call(&vm, 12, src2, 0, 32) != 0) return 7;
  if (memcmp(&vm.space[G_MEM_BASE >> 3], &vm.space[src2 >> 3], 4) != 0) return 8;

  /* seed x1 at reg file and test op10 READ_REGS */
  uint64_t x1 = G_REG_BASE + 32;
  vm_write_uint(&vm, x1, 32, 0x12345678u);
  uint64_t reg_dst = vm.workspace_base + 512;
  memset(&vm.space[reg_dst >> 3], 0, 8);
  if (ch_call(&vm, 10, reg_dst, 0, 0) != 0) return 9;
  if (memcmp(&vm.space[(reg_dst >> 3) + 4], &vm.space[x1 >> 3], 4) != 0) return 10;

  /* op8/op9 watchdog arm */
  if (ch_call(&vm, 8, 0, 0, 3) != 0) return 11;
  if (!vm_bit_get(&vm, vm.mmio.wd_enable)) return 12;
  if (ch_call(&vm, 9, 0, 0, 2) != 0) return 13;
  if (vm_read_uint(&vm, vm.mmio.wd_limit, vm.n_bits) != 2) return 14;

  /* negative: LOAD_CODE out-of-bounds destination */
  vm_bit_set(&vm, vm.mmio.ch_err, 0);
  vm_write_uint(&vm, vm.mmio.ch_c, vm.n_bits, 0);
  if (ch_call(&vm, 7, src, vm.space_bits, 8) != 0) return 15;
  if (!vm_bit_get(&vm, vm.mmio.ch_err)) return 16;
  if (vm_read_uint(&vm, vm.mmio.ch_c, vm.n_bits) != CH_E_BOUNDS) return 17;

  /* negative: READ_MEM out-of-bounds source */
  vm_bit_set(&vm, vm.mmio.ch_err, 0);
  vm_write_uint(&vm, vm.mmio.ch_c, vm.n_bits, 0);
  if (ch_call(&vm, 11, vm.space_bits, dst, 8) != 0) return 18;
  if (!vm_bit_get(&vm, vm.mmio.ch_err)) return 19;
  if (vm_read_uint(&vm, vm.mmio.ch_c, vm.n_bits) != CH_E_BOUNDS) return 20;

  vm_free(&vm);
  puts("OK rv32 runtime abi ops");
  return 0;
}
C

cc -O2 -I src/vm -o "$TMPDIR/abi_ops_check" \
  "$TMPDIR/abi_ops_check.c" src/vm/space.c src/vm/bitcpy.c

"$TMPDIR/abi_ops_check"
