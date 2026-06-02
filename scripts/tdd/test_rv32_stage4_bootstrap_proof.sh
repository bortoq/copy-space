#!/bin/sh
set -eu

TMPDIR="$(mktemp -d tmp/rv32_stage4_bootstrap.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

cat > "$TMPDIR/rv32_stage4_bootstrap_check.c" <<'C'
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "space.h"

static const uint64_t G_MEM_BASE = 0x002000ull;

enum {
  CH_OP_LOAD_CODE = 7,
  CH_OP_RUN = 8,
  CH_OP_READ_REGS = 10,
  CH_OP_READ_MEM = 11,
  CH_OP_TRACE_INFO = 13,
  CH_OP_TRACE_READ = 14
};

static int ch_call(vm_t *vm, unsigned op, uint64_t a, uint64_t b, uint64_t c) {
  vm_write_uint(vm, vm->mmio.ch_op, 8, op);
  vm_write_uint(vm, vm->mmio.ch_a, vm->addr_bits, a);
  vm_write_uint(vm, vm->mmio.ch_b, vm->addr_bits, b);
  vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, c);
  vm_bit_set(vm, vm->mmio.ch_req, 1);
  return vm_tick(vm, stdin, stdout) == VM_ERR ? -1 : 0;
}

static void wr32(vm_t *vm, uint64_t bit_addr, uint32_t v) {
  size_t b = (size_t)(bit_addr >> 3);
  vm->space[b] = (uint8_t)(v & 0xffu);
  vm->space[b + 1] = (uint8_t)((v >> 8) & 0xffu);
  vm->space[b + 2] = (uint8_t)((v >> 16) & 0xffu);
  vm->space[b + 3] = (uint8_t)((v >> 24) & 0xffu);
}

static uint32_t rd32(const uint8_t *p) {
  return (uint32_t)p[0] |
         ((uint32_t)p[1] << 8) |
         ((uint32_t)p[2] << 16) |
         ((uint32_t)p[3] << 24);
}

static uint32_t reg_from_buf(const uint8_t *regs, unsigned regno) {
  return rd32(regs + regno * 4u);
}

static uint32_t enc_lui(unsigned rd, uint32_t imm20) {
  return (imm20 << 12) | ((rd & 0x1fu) << 7) | 0x37u;
}

static uint32_t enc_auipc(unsigned rd, uint32_t imm20) {
  return (imm20 << 12) | ((rd & 0x1fu) << 7) | 0x17u;
}

static uint32_t enc_op_imm(unsigned rd, unsigned rs1, int imm, unsigned funct3) {
  return (((uint32_t)imm & 0xfffu) << 20) | ((rs1 & 0x1fu) << 15) |
         ((funct3 & 7u) << 12) | ((rd & 0x1fu) << 7) | 0x13u;
}

static uint32_t enc_shift_imm(unsigned rd, unsigned rs1, unsigned shamt, unsigned funct3, unsigned funct7) {
  return ((funct7 & 0x7fu) << 25) | ((shamt & 0x1fu) << 20) | ((rs1 & 0x1fu) << 15) |
         ((funct3 & 7u) << 12) | ((rd & 0x1fu) << 7) | 0x13u;
}

static uint32_t enc_op(unsigned rd, unsigned rs1, unsigned rs2, unsigned funct3, unsigned funct7) {
  return ((funct7 & 0x7fu) << 25) | ((rs2 & 0x1fu) << 20) | ((rs1 & 0x1fu) << 15) |
         ((funct3 & 7u) << 12) | ((rd & 0x1fu) << 7) | 0x33u;
}

static uint32_t enc_branch(unsigned rs1, unsigned rs2, int imm, unsigned funct3) {
  uint32_t u = (uint32_t)imm & 0x1fffu;
  return (((u >> 12) & 1u) << 31) |
         (((u >> 5) & 0x3fu) << 25) |
         ((rs2 & 0x1fu) << 20) |
         ((rs1 & 0x1fu) << 15) |
         ((funct3 & 7u) << 12) |
         (((u >> 1) & 0xfu) << 8) |
         (((u >> 11) & 1u) << 7) |
         0x63u;
}

static uint32_t enc_jalr(unsigned rd, unsigned rs1, int imm) {
  return (((uint32_t)imm & 0xfffu) << 20) | ((rs1 & 0x1fu) << 15) |
         (0u << 12) | ((rd & 0x1fu) << 7) | 0x67u;
}

static uint32_t enc_load(unsigned rd, unsigned rs1, int imm, unsigned funct3) {
  return (((uint32_t)imm & 0xfffu) << 20) | ((rs1 & 0x1fu) << 15) |
         ((funct3 & 7u) << 12) | ((rd & 0x1fu) << 7) | 0x03u;
}

static uint32_t enc_store(unsigned rs1, unsigned rs2, int imm, unsigned funct3) {
  uint32_t u = (uint32_t)imm & 0xfffu;
  return (((u >> 5) & 0x7fu) << 25) | ((rs2 & 0x1fu) << 20) |
         ((rs1 & 0x1fu) << 15) | ((funct3 & 7u) << 12) |
         ((u & 0x1fu) << 7) | 0x23u;
}

static int run_program(vm_t *vm, const uint32_t *prog, size_t n_words, unsigned max_ticks) {
  uint64_t src = vm->workspace_base + 2048;
  uint8_t *buf = &vm->space[src >> 3];
  memset(buf, 0, n_words * 4 + 16);
  for (size_t i = 0; i < n_words; i++) {
    buf[i * 4 + 0] = (uint8_t)(prog[i] & 0xffu);
    buf[i * 4 + 1] = (uint8_t)((prog[i] >> 8) & 0xffu);
    buf[i * 4 + 2] = (uint8_t)((prog[i] >> 16) & 0xffu);
    buf[i * 4 + 3] = (uint8_t)((prog[i] >> 24) & 0xffu);
  }

  if (ch_call(vm, CH_OP_LOAD_CODE, src, 0, (uint64_t)n_words * 32u) != 0) return 1;
  if (vm_bit_get(vm, vm->mmio.ch_err)) return 2;
  if (ch_call(vm, CH_OP_RUN, 0, 0, max_ticks) != 0) return 3;
  if (vm_bit_get(vm, vm->mmio.ch_err)) return 4;

  for (unsigned i = 0; i < max_ticks + 4; i++) {
    if (vm_bit_get(vm, vm->mmio.halt)) return 0;
    if (vm_tick(vm, stdin, stdout) == VM_ERR) return 5;
  }
  return 6;
}

static int fetch_regs(vm_t *vm, uint8_t *out_regs, size_t nbytes) {
  uint64_t dst = vm->workspace_base + 16384;
  memset(&vm->space[dst >> 3], 0, nbytes);
  if (ch_call(vm, CH_OP_READ_REGS, dst, 0, 0) != 0) return -1;
  if (vm_bit_get(vm, vm->mmio.ch_err)) return -1;
  memcpy(out_regs, &vm->space[dst >> 3], nbytes);
  return 0;
}

static int fetch_mem(vm_t *vm, uint64_t guest_off_bits, uint8_t *out_mem, size_t nbytes) {
  uint64_t dst = vm->workspace_base + 24576;
  memset(&vm->space[dst >> 3], 0, nbytes);
  if (ch_call(vm, CH_OP_READ_MEM, guest_off_bits, dst, (uint64_t)nbytes * 8u) != 0) return -1;
  if (vm_bit_get(vm, vm->mmio.ch_err)) return -1;
  memcpy(out_mem, &vm->space[dst >> 3], nbytes);
  return 0;
}

static int fetch_trace(vm_t *vm, rv_trace_info_t *info, rv_trace_record_t *records, size_t max_records) {
  uint64_t info_dst = vm->workspace_base + 32768;
  uint64_t trace_dst = vm->workspace_base + 36864;
  memset(&vm->space[info_dst >> 3], 0, sizeof(*info));
  if (ch_call(vm, CH_OP_TRACE_INFO, info_dst, 0, 0) != 0) return -1;
  if (vm_bit_get(vm, vm->mmio.ch_err)) return -1;
  memcpy(info, &vm->space[info_dst >> 3], sizeof(*info));
  if (info->version != 1u || info->record_bytes != sizeof(rv_trace_record_t)) return -1;
  if (info->record_count == 0u || info->record_count > max_records) return -1;
  memset(&vm->space[trace_dst >> 3], 0, info->used_bytes);
  if (ch_call(vm, CH_OP_TRACE_READ, 0, trace_dst, (uint64_t)info->used_bytes * 8u) != 0) return -1;
  if (vm_bit_get(vm, vm->mmio.ch_err)) return -1;
  memcpy(records, &vm->space[trace_dst >> 3], info->used_bytes);
  return 0;
}

static unsigned trace_opcode(const rv_trace_record_t *r) { return r->meta & 0x7fu; }
static unsigned trace_funct3(const rv_trace_record_t *r) { return (r->meta >> 7) & 0x7u; }
static unsigned trace_rd(const rv_trace_record_t *r) { return (r->meta >> 17) & 0x1fu; }
static unsigned trace_rs1(const rv_trace_record_t *r) { return (r->meta >> 22) & 0x1fu; }
static unsigned trace_rs2(const rv_trace_record_t *r) { return (r->meta >> 27) & 0x1fu; }
static unsigned trace_has_rd(const rv_trace_record_t *r) { return r->flags & 1u; }
static unsigned trace_has_mem_write(const rv_trace_record_t *r) { return (r->flags >> 1) & 1u; }
static unsigned trace_has_stop(const rv_trace_record_t *r) { return (r->flags >> 2) & 1u; }
static unsigned trace_mem_width(const rv_trace_record_t *r) { return (r->flags >> 8) & 0xffu; }
static unsigned trace_stop_reason(const rv_trace_record_t *r) { return (r->flags >> 16) & 0xffu; }

static int case_trace_and_abi(void) {
  vm_t vm;
  rv_trace_info_t info;
  rv_trace_record_t recs[64];
  uint8_t regs[32 * 4];

  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 10;

  const uint32_t prog[] = {
    enc_lui(1, 0x12345u),
    enc_auipc(2, 0u),
    enc_op_imm(3, 0, -1, 0),
    enc_op_imm(4, 3, 0, 2),
    0u
  };
  if (run_program(&vm, prog, sizeof(prog) / sizeof(prog[0]), 16) != 0) { vm_free(&vm); return 11; }
  if (fetch_regs(&vm, regs, sizeof(regs)) != 0) { vm_free(&vm); return 12; }
  if (fetch_trace(&vm, &info, recs, 64) != 0) { vm_free(&vm); return 13; }

  if (reg_from_buf(regs, 1) != 0x12345000u) { vm_free(&vm); return 14; }
  if (reg_from_buf(regs, 2) != 4u) { vm_free(&vm); return 15; }
  if (reg_from_buf(regs, 4) != 1u) { vm_free(&vm); return 16; }

  if (info.record_count != 5u) { vm_free(&vm); return 17; }
  if (trace_opcode(&recs[0]) != 0x37u || trace_rd(&recs[0]) != 1u || !trace_has_rd(&recs[0])) { vm_free(&vm); return 18; }
  if (recs[0].rd_value != 0x12345000u) { vm_free(&vm); return 19; }
  if (trace_opcode(&recs[1]) != 0x17u || trace_rd(&recs[1]) != 2u || recs[1].rd_value != 4u) { vm_free(&vm); return 20; }
  if (trace_opcode(&recs[2]) != 0x13u || trace_funct3(&recs[2]) != 0u || trace_rs1(&recs[2]) != 0u) { vm_free(&vm); return 21; }
  if (trace_opcode(&recs[3]) != 0x13u || trace_funct3(&recs[3]) != 2u || recs[3].rd_value != 1u) { vm_free(&vm); return 22; }
  if (!trace_has_stop(&recs[4]) || trace_stop_reason(&recs[4]) != RV_STOP_HALT || recs[4].instr != 0u) { vm_free(&vm); return 23; }

  vm_free(&vm);
  return 0;
}

static int case_control_matrix(void) {
  vm_t vm;
  rv_trace_info_t info;
  rv_trace_record_t recs[64];
  uint8_t regs[32 * 4];

  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 30;

  const uint32_t prog[] = {
    enc_op_imm(1, 0, 1, 0),
    enc_op_imm(2, 0, 2, 0),
    enc_branch(1, 2, 8, 4),
    enc_op_imm(3, 0, 99, 0),
    enc_branch(2, 1, 8, 5),
    enc_op_imm(4, 0, 99, 0),
    enc_op_imm(5, 0, -1, 0),
    enc_branch(1, 5, 8, 6),
    enc_op_imm(6, 0, 99, 0),
    enc_branch(5, 1, 8, 7),
    enc_op_imm(7, 0, 99, 0),
    enc_auipc(8, 0u),
    enc_op_imm(8, 8, 16, 0),
    enc_jalr(9, 8, 0),
    enc_op_imm(10, 0, 99, 0),
    enc_op_imm(10, 0, 42, 0),
    0u
  };
  if (run_program(&vm, prog, sizeof(prog) / sizeof(prog[0]), 64) != 0) { vm_free(&vm); return 31; }
  if (fetch_regs(&vm, regs, sizeof(regs)) != 0) { vm_free(&vm); return 32; }
  if (fetch_trace(&vm, &info, recs, 64) != 0) { vm_free(&vm); return 33; }

  if (reg_from_buf(regs, 3) != 0u || reg_from_buf(regs, 4) != 0u || reg_from_buf(regs, 6) != 0u || reg_from_buf(regs, 7) != 0u) { vm_free(&vm); return 34; }
  if (reg_from_buf(regs, 9) != 56u || reg_from_buf(regs, 10) != 42u) { vm_free(&vm); return 35; }
  if (info.record_count != 12u) { vm_free(&vm); return 36; }
  if (trace_opcode(&recs[2]) != 0x63u || trace_funct3(&recs[2]) != 4u) { vm_free(&vm); return 37; }
  if (trace_opcode(&recs[3]) != 0x63u || trace_funct3(&recs[3]) != 5u) { vm_free(&vm); return 38; }
  if (trace_opcode(&recs[5]) != 0x63u || trace_funct3(&recs[5]) != 6u) { vm_free(&vm); return 39; }
  if (trace_opcode(&recs[6]) != 0x63u || trace_funct3(&recs[6]) != 7u) { vm_free(&vm); return 40; }
  if (trace_opcode(&recs[9]) != 0x67u || trace_rd(&recs[9]) != 9u || recs[9].rd_value != 56u) { vm_free(&vm); return 41; }
  if (!trace_has_stop(&recs[11]) || trace_stop_reason(&recs[11]) != RV_STOP_HALT) { vm_free(&vm); return 42; }

  vm_free(&vm);
  return 0;
}

static int case_memory_and_faults(void) {
  vm_t vm;
  rv_trace_info_t info;
  rv_trace_record_t recs[64];
  uint8_t regs[32 * 4];
  uint8_t mem[8];

  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 50;

  const uint32_t prog[] = {
    enc_op_imm(1, 0, 128, 0),
    enc_op_imm(2, 0, -1, 0),
    enc_store(1, 2, 0, 0),
    enc_op_imm(3, 0, -128, 0),
    enc_store(1, 3, 1, 0),
    enc_lui(4, 0x8u),
    enc_op_imm(4, 4, 1, 0),
    enc_store(1, 4, 2, 1),
    enc_load(5, 1, 0, 0),
    enc_load(6, 1, 0, 4),
    enc_load(7, 1, 1, 0),
    enc_load(8, 1, 1, 4),
    enc_load(9, 1, 2, 1),
    enc_load(10, 1, 2, 5),
    0u
  };
  if (run_program(&vm, prog, sizeof(prog) / sizeof(prog[0]), 64) != 0) { vm_free(&vm); return 51; }
  if (fetch_regs(&vm, regs, sizeof(regs)) != 0) { vm_free(&vm); return 52; }
  if (fetch_mem(&vm, 128u * 8u, mem, sizeof(mem)) != 0) { vm_free(&vm); return 53; }
  if (fetch_trace(&vm, &info, recs, 64) != 0) { vm_free(&vm); return 54; }

  if (mem[0] != 0xffu || mem[1] != 0x80u || rd32(mem + 2) != 0x00008001u) { vm_free(&vm); return 55; }
  if (reg_from_buf(regs, 5) != 0xffffffffu || reg_from_buf(regs, 6) != 255u) { vm_free(&vm); return 56; }
  if (reg_from_buf(regs, 7) != 0xffffff80u || reg_from_buf(regs, 8) != 128u) { vm_free(&vm); return 57; }
  if (reg_from_buf(regs, 9) != 0xffff8001u || reg_from_buf(regs, 10) != 0x8001u) { vm_free(&vm); return 58; }
  if (trace_opcode(&recs[2]) != 0x23u || !trace_has_mem_write(&recs[2]) || trace_mem_width(&recs[2]) != 1u) { vm_free(&vm); return 59; }
  if (trace_opcode(&recs[4]) != 0x23u || !trace_has_mem_write(&recs[4]) || trace_mem_width(&recs[4]) != 1u) { vm_free(&vm); return 60; }
  if (trace_opcode(&recs[7]) != 0x23u || !trace_has_mem_write(&recs[7]) || trace_mem_width(&recs[7]) != 2u) { vm_free(&vm); return 61; }
  if (trace_opcode(&recs[8]) != 0x03u || trace_funct3(&recs[8]) != 0u || reg_from_buf(regs, 5) != recs[8].rd_value) { vm_free(&vm); return 62; }
  if (trace_opcode(&recs[13]) != 0x03u || trace_funct3(&recs[13]) != 5u || reg_from_buf(regs, 10) != recs[13].rd_value) { vm_free(&vm); return 63; }
  if (!trace_has_stop(&recs[14]) || trace_stop_reason(&recs[14]) != RV_STOP_HALT) { vm_free(&vm); return 64; }
  vm_free(&vm);

  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 65;
  {
    const uint32_t prog_align[] = {
      enc_op_imm(1, 0, 33, 0),
      enc_load(2, 1, 0, 1),
      0u
    };
    if (run_program(&vm, prog_align, sizeof(prog_align) / sizeof(prog_align[0]), 16) != 0) { vm_free(&vm); return 66; }
    if (fetch_trace(&vm, &info, recs, 64) != 0) { vm_free(&vm); return 67; }
    if (!trace_has_stop(&recs[1]) || trace_stop_reason(&recs[1]) != RV_STOP_ALIGN) { vm_free(&vm); return 68; }
  }
  vm_free(&vm);

  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 69;
  {
    const uint32_t prog_bounds[] = {
      enc_lui(1, 0xffff0u),
      enc_load(2, 1, 0, 2),
      0u
    };
    if (run_program(&vm, prog_bounds, sizeof(prog_bounds) / sizeof(prog_bounds[0]), 16) != 0) { vm_free(&vm); return 70; }
    if (fetch_trace(&vm, &info, recs, 64) != 0) { vm_free(&vm); return 71; }
    if (!trace_has_stop(&recs[1]) || trace_stop_reason(&recs[1]) != RV_STOP_BOUNDS) { vm_free(&vm); return 72; }
  }
  vm_free(&vm);

  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 73;
  {
    const uint32_t prog_unsupported[] = { 0x0000000fu, 0u };
    if (run_program(&vm, prog_unsupported, sizeof(prog_unsupported) / sizeof(prog_unsupported[0]), 16) != 0) { vm_free(&vm); return 74; }
    if (fetch_trace(&vm, &info, recs, 64) != 0) { vm_free(&vm); return 75; }
    if (!trace_has_stop(&recs[0]) || trace_stop_reason(&recs[0]) != RV_STOP_UNSUPPORTED) { vm_free(&vm); return 76; }
  }
  vm_free(&vm);

  return 0;
}

static int case_replay(void) {
  vm_t vm1, vm2;
  rv_trace_info_t i1, i2;
  rv_trace_record_t t1[32], t2[32];

  const uint32_t prog[] = {
    enc_op_imm(1, 0, 5, 0),
    enc_op_imm(2, 1, 7, 0),
    0u
  };

  if (vm_init(&vm1, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 80;
  if (run_program(&vm1, prog, sizeof(prog) / sizeof(prog[0]), 16) != 0) { vm_free(&vm1); return 81; }
  if (fetch_trace(&vm1, &i1, t1, 32) != 0) { vm_free(&vm1); return 82; }
  vm_free(&vm1);

  if (vm_init(&vm2, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 83;
  if (run_program(&vm2, prog, sizeof(prog) / sizeof(prog[0]), 16) != 0) { vm_free(&vm2); return 84; }
  if (fetch_trace(&vm2, &i2, t2, 32) != 0) { vm_free(&vm2); return 85; }
  vm_free(&vm2);

  if (i1.record_count != i2.record_count || i1.used_bytes != i2.used_bytes) return 86;
  if (memcmp(t1, t2, i1.used_bytes) != 0) return 87;
  return 0;
}

int main(void) {
  int rc = case_trace_and_abi();
  if (rc != 0) return rc;
  rc = case_control_matrix();
  if (rc != 0) return rc;
  rc = case_memory_and_faults();
  if (rc != 0) return rc;
  rc = case_replay();
  if (rc != 0) return rc;
  puts("OK rv32 stage4 bootstrap proof");
  return 0;
}
C

cc -O2 -I src/vm -o "$TMPDIR/rv32_stage4_bootstrap_check" \
  "$TMPDIR/rv32_stage4_bootstrap_check.c" src/vm/space.c src/vm/bitcpy.c

"$TMPDIR/rv32_stage4_bootstrap_check"
