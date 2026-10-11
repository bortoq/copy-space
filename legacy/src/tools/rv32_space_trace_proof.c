// rv32_space_trace_proof.c - resident trace/state proof gate for space.c
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

static void init_addi_case(vm_t *vm) {
  // ADDI x1, x0, 5 = 0x00500093, little-endian in guest memory.
  wr_u8(vm, G_MEM_BASE + 0u, 0x93);
  wr_u8(vm, G_MEM_BASE + 8u, 0x00);
  wr_u8(vm, G_MEM_BASE + 16u, 0x50);
  wr_u8(vm, G_MEM_BASE + 24u, 0x00);

  // PC = 0
  wr_u8(vm, G_PC + 0u, 0x00);
  wr_u8(vm, G_PC + 8u, 0x00);
  wr_u8(vm, G_PC + 16u, 0x00);
  wr_u8(vm, G_PC + 24u, 0x00);

  for (unsigned i = 0; i < 32; i++) {
    wr_u8(vm, G_REG_BASE + (bitaddr_t)i * 8u, 0x00);
  }

  vm->rv_guest_loaded = 1;
  vm->rv_guest_running = 1;
  vm->rv_guest_steps = 0;
  vm->rv_guest_stop_reason = RV_STOP_NONE;
  vm_bit_set(vm, vm->mmio.halt, 0);
}

static void fail(const char *msg) {
  fprintf(stderr, "%s\n", msg);
}

static void ch_write8(vm_t *vm, bitaddr_t pos, uint64_t value) {
  vm_write_uint(vm, pos, 8u, value);
}

static void ch_write_addr(vm_t *vm, bitaddr_t pos, uint64_t value) {
  vm_write_uint(vm, pos, vm->addr_bits, value);
}

int main(void) {
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) {
    fail("vm_init failed");
    return 1;
  }

  init_addi_case(&vm);

  if (vm_tick(&vm, stdin, stdout) != VM_OK) {
    fail("vm_tick(addi) failed");
    vm_free(&vm);
    return 1;
  }

  if (rd_u8(&vm, G_REG_BASE + 32u) != 0x05) {
    fprintf(stderr, "x1 not written by resident ADDI; mem=%02x%02x%02x%02x pc=%02x%02x%02x%02x stop=%u steps=%llu reg1=%02x%02x%02x%02x\n",
            rd_u8(&vm, G_MEM_BASE + 0u), rd_u8(&vm, G_MEM_BASE + 8u),
            rd_u8(&vm, G_MEM_BASE + 16u), rd_u8(&vm, G_MEM_BASE + 24u),
            rd_u8(&vm, G_PC + 0u), rd_u8(&vm, G_PC + 8u),
            rd_u8(&vm, G_PC + 16u), rd_u8(&vm, G_PC + 24u),
            (unsigned)vm.rv_guest_stop_reason,
            (unsigned long long)vm.rv_guest_steps,
            rd_u8(&vm, G_REG_BASE + 32u), rd_u8(&vm, G_REG_BASE + 40u),
            rd_u8(&vm, G_REG_BASE + 48u), rd_u8(&vm, G_REG_BASE + 56u));
    vm_free(&vm);
    return 1;
  }
  if (rd_u8(&vm, G_PC + 0u) != 0x04 || rd_u8(&vm, G_PC + 8u) != 0x00 ||
      rd_u8(&vm, G_PC + 16u) != 0x00 || rd_u8(&vm, G_PC + 24u) != 0x00) {
    fail("PC not advanced by resident ADDI");
    vm_free(&vm);
    return 1;
  }
  if (vm.rv_guest_steps != 1u) {
    fprintf(stderr, "expected steps=1, got=%llu\n", (unsigned long long)vm.rv_guest_steps);
    vm_free(&vm);
    return 1;
  }

  if (vm.rv_trace_count == 0u) {
    fail("no resident trace records emitted");
    vm_free(&vm);
    return 1;
  }
  const rv_trace_record_t rec = vm.rv_trace_records[0];
  uint32_t x1 = (uint32_t)rd_u8(&vm, G_REG_BASE + 32u) |
                ((uint32_t)rd_u8(&vm, G_REG_BASE + 40u) << 8) |
                ((uint32_t)rd_u8(&vm, G_REG_BASE + 48u) << 16) |
                ((uint32_t)rd_u8(&vm, G_REG_BASE + 56u) << 24);
  if (rec.step != 1u || rec.pc != 0u || rec.instr != 0x00500093u || rec.rd_value != x1) {
    fprintf(stderr, "trace/state mismatch: step=%u pc=%08x instr=%08x rd=%08x x1=%08x\n",
            rec.step, rec.pc, rec.instr, rec.rd_value, x1);
    vm_free(&vm);
    return 1;
  }

  bitaddr_t info_dst = vm.workspace_base + 0u;
  bitaddr_t data_dst = vm.workspace_base + 256u;
  ch_write8(&vm, vm.mmio.ch_op, 13u);
  ch_write_addr(&vm, vm.mmio.ch_a, info_dst);
  vm_bit_set(&vm, vm.mmio.ch_req, 1);
  if (vm_tick(&vm, stdin, stdout) == VM_ERR) {
    fail("TRACE_INFO ABI failed");
    vm_free(&vm);
    return 1;
  }

  rv_trace_info_t info;
  memcpy(&info, &vm.space[info_dst >> 3], sizeof(info));
  if (info.version != 1u || info.record_bytes != sizeof(rv_trace_record_t) ||
      info.record_count == 0u || info.used_bytes < sizeof(rv_trace_record_t)) {
    fprintf(stderr, "bad trace info: v=%u bytes=%u count=%u used=%u\n",
            info.version, info.record_bytes, info.record_count, info.used_bytes);
    vm_free(&vm);
    return 1;
  }

  ch_write8(&vm, vm.mmio.ch_op, 14u);
  ch_write_addr(&vm, vm.mmio.ch_a, 0u);
  ch_write_addr(&vm, vm.mmio.ch_b, data_dst);
  vm_write_uint(&vm, vm.mmio.ch_c, vm.n_bits, sizeof(rv_trace_record_t) * 8u);
  vm_bit_set(&vm, vm.mmio.ch_req, 1);
  if (vm_tick(&vm, stdin, stdout) == VM_ERR) {
    fail("TRACE_READ ABI failed");
    vm_free(&vm);
    return 1;
  }

  rv_trace_record_t abi_rec;
  memcpy(&abi_rec, &vm.space[data_dst >> 3], sizeof(abi_rec));
  if (memcmp(&abi_rec, &rec, sizeof(rec)) != 0) {
    fail("TRACE_READ bytes do not match resident trace record");
    vm_free(&vm);
    return 1;
  }

  puts("OK rv32 space trace proof");
  vm_free(&vm);
  return 0;
}
