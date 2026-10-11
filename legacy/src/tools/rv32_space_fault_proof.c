// rv32_space_fault_proof.c - minimal resident space.c proof harness for fault paths
#include "space.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum {
  G_PC          = 0x001000u,
  G_REG_BASE    = 0x001200u,
  G_MEM_BASE    = 0x002000u
};

static void wr_u8(vm_t *vm, bitaddr_t bitpos, uint8_t v) {
  vm_write_uint(vm, bitpos, 8u, v);
}

static uint8_t rd_u8(const vm_t *vm, bitaddr_t bitpos) {
  return (uint8_t)vm_read_uint(vm, bitpos, 8u);
}

static void init_lw_align_case(vm_t *vm) {
  // LW x1, 2(x0) = 0x00202083, stored little-endian in memory
  wr_u8(vm, G_MEM_BASE + 0u, 0x83);
  wr_u8(vm, G_MEM_BASE + 8u, 0x20);
  wr_u8(vm, G_MEM_BASE + 16u, 0x20);
  wr_u8(vm, G_MEM_BASE + 24u, 0x00);

  wr_u8(vm, G_PC + 0u, 0x00);
  wr_u8(vm, G_PC + 8u, 0x00);
  wr_u8(vm, G_PC + 16u, 0x00);
  wr_u8(vm, G_PC + 24u, 0x00);

  for (unsigned i = 0; i < 8; i++) {
    wr_u8(vm, G_REG_BASE + (bitaddr_t)i * 8u, 0x00);
  }
  vm->rv_guest_loaded = 1;
  vm->rv_guest_running = 1;
  vm->rv_guest_steps = 0;
  vm->rv_guest_stop_reason = RV_STOP_NONE;
  vm_bit_set(vm, vm->mmio.halt, 0);
}

static void init_lw_bounds_case(vm_t *vm) {
  // LW x2, 0(x1) = 0x0000a103 with x1 set beyond the guest memory window.
  wr_u8(vm, G_MEM_BASE + 0u, 0x03);
  wr_u8(vm, G_MEM_BASE + 8u, 0xa1);
  wr_u8(vm, G_MEM_BASE + 16u, 0x00);
  wr_u8(vm, G_MEM_BASE + 24u, 0x00);

  wr_u8(vm, G_PC + 0u, 0x00);
  wr_u8(vm, G_PC + 8u, 0x00);
  wr_u8(vm, G_PC + 16u, 0x00);
  wr_u8(vm, G_PC + 24u, 0x00);

  for (unsigned i = 0; i < 8; i++) {
    wr_u8(vm, G_REG_BASE + (bitaddr_t)i * 8u, 0x00);
  }
  // x1 = 0xFFFFFFFC so addr is aligned but still out of the guest memory window.
  wr_u8(vm, G_REG_BASE + 32u, 0xfc);
  wr_u8(vm, G_REG_BASE + 40u, 0xff);
  wr_u8(vm, G_REG_BASE + 48u, 0xff);
  wr_u8(vm, G_REG_BASE + 56u, 0xff);

  vm->rv_guest_loaded = 1;
  vm->rv_guest_running = 1;
  vm->rv_guest_steps = 0;
  vm->rv_guest_stop_reason = RV_STOP_NONE;
  vm_bit_set(vm, vm->mmio.halt, 0);
}

int main(int argc, char **argv) {
  const char *which = (argc > 1) ? argv[1] : "align";
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) {
    fprintf(stderr, "vm_init failed\n");
    return 1;
  }

  if (!strcmp(which, "align")) {
    init_lw_align_case(&vm);
  } else if (!strcmp(which, "bounds")) {
    init_lw_bounds_case(&vm);
  } else {
    fprintf(stderr, "usage: %s [align|bounds]\n", argv[0]);
    vm_free(&vm);
    return 2;
  }

  vm_rc_t rc = vm_tick(&vm, stdin, stdout);
  if (rc == VM_ERR) {
    fprintf(stderr, "vm_tick failed\n");
    vm_free(&vm);
    return 1;
  }

  rv_stop_reason_t expect = !strcmp(which, "align") ? RV_STOP_ALIGN : RV_STOP_BOUNDS;
  if (vm.rv_guest_stop_reason != expect) {
    fprintf(stderr, "expected stop=%u, got=%u\n", (unsigned)expect, (unsigned)vm.rv_guest_stop_reason);
    vm_free(&vm);
    return 1;
  }

  if (rd_u8(&vm, G_PC + 0u) != 0x00 || rd_u8(&vm, G_PC + 8u) != 0x00 ||
      rd_u8(&vm, G_PC + 16u) != 0x00 || rd_u8(&vm, G_PC + 24u) != 0x00) {
    fprintf(stderr, "PC unexpectedly changed on alignment fault\n");
    vm_free(&vm);
    return 1;
  }

  if (!strcmp(which, "align")) puts("OK rv32 space align fault");
  else puts("OK rv32 space bounds fault");
  vm_free(&vm);
  return 0;
}
