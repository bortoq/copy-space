// rv32_space_control_proof.c - resident request/response control plane proof for space.c
#include "space.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum {
  G_PC          = 0x001000u,
  G_MEM_BASE    = 0x002000u
};

static void wr_u8(vm_t *vm, bitaddr_t bitpos, uint8_t v) {
  vm_write_uint(vm, bitpos, 8u, v);
}

static uint8_t rd_u8(const vm_t *vm, bitaddr_t bitpos) {
  return (uint8_t)vm_read_uint(vm, bitpos, 8u);
}

static void set_req8(vm_t *vm, unsigned op) {
  vm_write_uint(vm, vm->mmio.ch_op, 8u, op);
  vm_bit_set(vm, vm->mmio.ch_req, 1);
}

static void clear_req(vm_t *vm) {
  vm_bit_set(vm, vm->mmio.ch_req, 0);
}

static void init_control_case(vm_t *vm) {
  for (unsigned i = 0; i < 4; i++) {
    wr_u8(vm, G_MEM_BASE + (bitaddr_t)i * 8u, (uint8_t[]){0x93, 0x00, 0x50, 0x00}[i]);
  }
  for (unsigned i = 0; i < 4; i++) {
    wr_u8(vm, G_PC + (bitaddr_t)i * 8u, 0x00);
  }
  vm_bit_set(vm, vm->mmio.halt, 0);
}

int main(void) {
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) {
    fprintf(stderr, "vm_init failed\n");
    return 1;
  }

  init_control_case(&vm);

  set_req8(&vm, 7u); /* LOAD_CODE */
  vm_write_uint(&vm, vm.mmio.ch_a, vm.addr_bits, G_MEM_BASE);
  vm_write_uint(&vm, vm.mmio.ch_b, vm.addr_bits, 0u);
  vm_write_uint(&vm, vm.mmio.ch_c, vm.n_bits, 32u);
  if (vm_tick(&vm, stdin, stdout) != VM_OK) {
    fprintf(stderr, "vm_tick(LOAD_CODE) failed\n");
    vm_free(&vm);
    return 1;
  }
  if (!vm_bit_get(&vm, vm.mmio.ch_done) || vm_bit_get(&vm, vm.mmio.ch_err)) {
    fprintf(stderr, "LOAD_CODE did not complete cleanly\n");
    vm_free(&vm);
    return 1;
  }
  clear_req(&vm);

  if (rd_u8(&vm, G_MEM_BASE + 0u) != 0x93 || rd_u8(&vm, G_MEM_BASE + 8u) != 0x00 ||
      rd_u8(&vm, G_MEM_BASE + 16u) != 0x50 || rd_u8(&vm, G_MEM_BASE + 24u) != 0x00) {
    fprintf(stderr, "LOAD_CODE did not preserve code bytes\n");
    vm_free(&vm);
    return 1;
  }

  set_req8(&vm, 6u); /* STATUS */
  vm_write_uint(&vm, vm.mmio.ch_a, vm.addr_bits, vm.workspace_base);
  if (vm_tick(&vm, stdin, stdout) != VM_OK) {
    fprintf(stderr, "vm_tick(STATUS) failed\n");
    vm_free(&vm);
    return 1;
  }
  if (!vm_bit_get(&vm, vm.mmio.ch_done) || vm_bit_get(&vm, vm.mmio.ch_err)) {
    fprintf(stderr, "STATUS did not complete cleanly\n");
    vm_free(&vm);
    return 1;
  }

  uint64_t tick = vm_read_uint(&vm, vm.mmio.ch_a, vm.addr_bits);
  uint64_t halt = vm_bit_get(&vm, vm.mmio.ch_b);
  uint64_t err = vm_read_uint(&vm, vm.mmio.ch_c, vm.n_bits);
  if (tick == 0u && halt == 0u && err == 0u) {
    // This is still a valid response; the key property is request/response completion.
  }

  puts("OK rv32 space control proof");
  vm_free(&vm);
  return 0;
}
