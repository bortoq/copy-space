// resident_job_descriptor_proof.c - proof gate for resident job descriptor format
#include "space.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum {
  G_MEM_BASE = 0x002000u
};

typedef struct {
  uint32_t kind;
  uint32_t entry;
  uint32_t arg0;
  uint32_t arg1;
  uint32_t flags;
} resident_job_desc_t;

static void wr_u32le(uint8_t *dst, uint32_t v) {
  dst[0] = (uint8_t)(v & 0xffu);
  dst[1] = (uint8_t)((v >> 8) & 0xffu);
  dst[2] = (uint8_t)((v >> 16) & 0xffu);
  dst[3] = (uint8_t)((v >> 24) & 0xffu);
}

static uint32_t rd_u32le(const uint8_t *src) {
  return (uint32_t)src[0] |
         ((uint32_t)src[1] << 8) |
         ((uint32_t)src[2] << 16) |
         ((uint32_t)src[3] << 24);
}

static void write_desc(vm_t *vm, bitaddr_t dst, const resident_job_desc_t *d) {
  uint8_t *p = &vm->space[dst >> 3];
  wr_u32le(p + 0u, d->kind);
  wr_u32le(p + 4u, d->entry);
  wr_u32le(p + 8u, d->arg0);
  wr_u32le(p + 12u, d->arg1);
  wr_u32le(p + 16u, d->flags);
}

static void set_req8(vm_t *vm, unsigned op) {
  vm_write_uint(vm, vm->mmio.ch_op, 8u, op);
  vm_bit_set(vm, vm->mmio.ch_req, 1);
}

int main(void) {
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) {
    fprintf(stderr, "vm_init failed\n");
    return 1;
  }

  const resident_job_desc_t desc = {
    .kind = 1u,
    .entry = 0x1000u,
    .arg0 = 0x11223344u,
    .arg1 = 0xaabbccddu,
    .flags = 0x00000001u
  };

  bitaddr_t src = vm.workspace_base + 0u;
  bitaddr_t dst = vm.workspace_base + 256u;
  write_desc(&vm, src, &desc);

  set_req8(&vm, 7u); /* LOAD_CODE */
  vm_write_uint(&vm, vm.mmio.ch_a, vm.addr_bits, src);
  vm_write_uint(&vm, vm.mmio.ch_b, vm.addr_bits, 0u);
  vm_write_uint(&vm, vm.mmio.ch_c, vm.n_bits, (uint64_t)sizeof(desc) * 8u);
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

  set_req8(&vm, 11u); /* READ_MEM */
  vm_write_uint(&vm, vm.mmio.ch_a, vm.addr_bits, 0u);
  vm_write_uint(&vm, vm.mmio.ch_b, vm.addr_bits, dst);
  vm_write_uint(&vm, vm.mmio.ch_c, vm.n_bits, (uint64_t)sizeof(desc) * 8u);
  if (vm_tick(&vm, stdin, stdout) != VM_OK) {
    fprintf(stderr, "vm_tick(READ_MEM) failed\n");
    vm_free(&vm);
    return 1;
  }
  if (!vm_bit_get(&vm, vm.mmio.ch_done) || vm_bit_get(&vm, vm.mmio.ch_err)) {
    fprintf(stderr, "READ_MEM did not complete cleanly\n");
    vm_free(&vm);
    return 1;
  }

  const uint8_t *blob = &vm.space[dst >> 3];
  resident_job_desc_t got = {
    .kind = rd_u32le(blob + 0u),
    .entry = rd_u32le(blob + 4u),
    .arg0 = rd_u32le(blob + 8u),
    .arg1 = rd_u32le(blob + 12u),
    .flags = rd_u32le(blob + 16u)
  };
  if (got.kind != desc.kind || got.entry != desc.entry ||
      got.arg0 != desc.arg0 || got.arg1 != desc.arg1 || got.flags != desc.flags) {
    fprintf(stderr, "resident job descriptor transport mismatch\n");
    vm_free(&vm);
    return 1;
  }

  puts("OK resident job descriptor proof");
  vm_free(&vm);
  return 0;
}
