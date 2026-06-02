#!/bin/sh
set -eu

TMPDIR="$(mktemp -d tmp/rv32_stage3_runtime.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

cat > "$TMPDIR/rv32i_stage3_check.c" <<'C'
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "space.h"

static const uint64_t G_PC = 0x001000ull;
static const uint64_t G_REG_BASE = 0x001200ull;
static const uint64_t G_MEM_BASE = 0x002000ull;

static int ch_call(vm_t *vm, unsigned op, uint64_t a, uint64_t b, uint64_t c) {
  vm_write_uint(vm, vm->mmio.ch_op, 8, op);
  vm_write_uint(vm, vm->mmio.ch_a, vm->addr_bits, a);
  vm_write_uint(vm, vm->mmio.ch_b, vm->addr_bits, b);
  vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, c);
  vm_bit_set(vm, vm->mmio.ch_req, 1);
  return vm_tick(vm, stdin, stdout) == VM_ERR ? -1 : 0;
}

static uint32_t rd32(const vm_t *vm, uint64_t bit_addr) {
  size_t b = (size_t)(bit_addr >> 3);
  return (uint32_t)vm->space[b] |
         ((uint32_t)vm->space[b + 1] << 8) |
         ((uint32_t)vm->space[b + 2] << 16) |
         ((uint32_t)vm->space[b + 3] << 24);
}

static uint16_t rd16(const vm_t *vm, uint64_t bit_addr) {
  size_t b = (size_t)(bit_addr >> 3);
  return (uint16_t)vm->space[b] | (uint16_t)(vm->space[b + 1] << 8);
}

static uint8_t rd8(const vm_t *vm, uint64_t bit_addr) {
  return vm->space[(size_t)(bit_addr >> 3)];
}

static void wr32(vm_t *vm, uint64_t bit_addr, uint32_t v) {
  size_t b = (size_t)(bit_addr >> 3);
  vm->space[b] = (uint8_t)(v & 0xffu);
  vm->space[b + 1] = (uint8_t)((v >> 8) & 0xffu);
  vm->space[b + 2] = (uint8_t)((v >> 16) & 0xffu);
  vm->space[b + 3] = (uint8_t)((v >> 24) & 0xffu);
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

  if (ch_call(vm, 7, src, 0, (uint64_t)n_words * 32u) != 0) return 1;
  if (vm_bit_get(vm, vm->mmio.ch_err)) return 2;
  if (ch_call(vm, 8, 0, 0, max_ticks) != 0) return 3;

  for (unsigned i = 0; i < max_ticks + 4; i++) {
    if (vm_bit_get(vm, vm->mmio.halt)) return 0;
    if (vm_tick(vm, stdin, stdout) == VM_ERR) return 4;
  }
  return 5;
}

static uint32_t reg32(const vm_t *vm, unsigned regno) {
  return rd32(vm, G_REG_BASE + (uint64_t)regno * 32u);
}

static int case_alu(void) {
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 10;
  wr32(&vm, G_REG_BASE + 0u, 0xdeadbeefu);

  const uint32_t prog[] = {
    enc_lui(1, 0x12345u),
    enc_auipc(2, 0u),
    enc_op_imm(3, 0, -1, 0),              /* addi */
    enc_op_imm(4, 3, 0, 2),               /* slti */
    enc_op_imm(5, 3, 1, 3),               /* sltiu */
    enc_op_imm(6, 3, 0x0f0, 4),           /* xori */
    enc_op_imm(7, 0, 0x120, 6),           /* ori */
    enc_op_imm(8, 6, 0x0ff, 7),           /* andi */
    enc_shift_imm(9, 8, 4, 1, 0x00),      /* slli */
    enc_shift_imm(10, 9, 4, 5, 0x00),     /* srli */
    enc_op_imm(11, 0, -16, 0),            /* addi */
    enc_shift_imm(12, 11, 2, 5, 0x20),    /* srai */
    enc_op(13, 11, 8, 2, 0x00),           /* slt */
    enc_op(14, 3, 8, 3, 0x00),            /* sltu */
    enc_op(19, 0, 0, 0, 0x00),            /* add x19,x0,x0 */
    enc_op_imm(19, 19, 2, 0),             /* addi x19,2 */
    enc_op(15, 9, 10, 4, 0x00),           /* xor */
    enc_op(16, 15, 7, 6, 0x00),           /* or */
    enc_op(17, 16, 7, 7, 0x00),           /* and */
    enc_op(20, 10, 19, 1, 0x00),          /* sll */
    enc_op(21, 20, 19, 5, 0x00),          /* srl */
    enc_op(22, 11, 19, 5, 0x20),          /* sra */
    0u
  };

  int rc = run_program(&vm, prog, sizeof(prog) / sizeof(prog[0]), 64);
  if (rc != 0) { vm_free(&vm); return 11 + rc; }

  if (reg32(&vm, 0) != 0u) { vm_free(&vm); return 20; }
  if (reg32(&vm, 1) != 0x12345000u) { vm_free(&vm); return 21; }
  if (reg32(&vm, 2) != 4u) { vm_free(&vm); return 22; }
  if (reg32(&vm, 4) != 1u) { vm_free(&vm); return 23; }
  if (reg32(&vm, 5) != 0u) { vm_free(&vm); return 24; }
  if (reg32(&vm, 8) != 0x0fu) { vm_free(&vm); return 25; }
  if (reg32(&vm, 9) != 0xf0u) { vm_free(&vm); return 26; }
  if (reg32(&vm, 10) != 0x0fu) { vm_free(&vm); return 27; }
  if (reg32(&vm, 12) != 0xfffffffcu) { vm_free(&vm); return 28; }
  if (reg32(&vm, 13) != 1u) { vm_free(&vm); return 29; }
  if (reg32(&vm, 14) != 0u) { vm_free(&vm); return 30; }
  if (reg32(&vm, 15) != 0xffu) { vm_free(&vm); return 31; }
  if (reg32(&vm, 16) != 0x1ffu) { vm_free(&vm); return 32; }
  if (reg32(&vm, 17) != 0x120u) { vm_free(&vm); return 33; }
  if (reg32(&vm, 20) != 0x3cu) { vm_free(&vm); return 34; }
  if (reg32(&vm, 21) != 0x0fu) { vm_free(&vm); return 35; }
  if (reg32(&vm, 22) != 0xfffffffcu) { vm_free(&vm); return 36; }
  if (rd32(&vm, G_PC) != 22u * 4u) { vm_free(&vm); return 37; }
  if (vm.rv_guest_steps != 22u) { vm_free(&vm); return 38; }
  if (vm.rv_guest_stop_reason != RV_STOP_HALT) { vm_free(&vm); return 39; }

  vm_free(&vm);
  return 0;
}

static int case_control(void) {
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 40;

  const uint32_t prog[] = {
    enc_op_imm(1, 0, 1, 0),               /* pc 0 */
    enc_op_imm(2, 0, 2, 0),               /* pc 4 */
    enc_branch(1, 2, 8, 4),               /* blt -> pc 16 */
    enc_op_imm(3, 0, 99, 0),              /* skipped */
    enc_branch(2, 1, 8, 5),               /* bge -> pc 24 */
    enc_op_imm(4, 0, 99, 0),              /* skipped */
    enc_op_imm(5, 0, -1, 0),              /* pc 24 */
    enc_branch(1, 5, 8, 6),               /* bltu -> pc 36 */
    enc_op_imm(6, 0, 99, 0),              /* skipped */
    enc_branch(5, 1, 8, 7),               /* bgeu -> pc 48 */
    enc_op_imm(7, 0, 99, 0),              /* skipped */
    enc_auipc(8, 0u),                     /* pc 44 */
    enc_op_imm(8, 8, 16, 0),              /* x8 = 60 */
    enc_jalr(9, 8, 0),                    /* pc -> 60, x9=56 */
    enc_op_imm(10, 0, 99, 0),             /* skipped by jalr */
    enc_op_imm(10, 0, 42, 0),             /* pc 60? target 52 actually */
    0u
  };

  int rc = run_program(&vm, prog, sizeof(prog) / sizeof(prog[0]), 64);
  if (rc != 0) { vm_free(&vm); return 41 + rc; }

  if (reg32(&vm, 3) != 0u || reg32(&vm, 4) != 0u || reg32(&vm, 6) != 0u || reg32(&vm, 7) != 0u) {
    vm_free(&vm); return 50;
  }
  if (reg32(&vm, 9) != 56u) { vm_free(&vm); return 51; }
  if (reg32(&vm, 10) != 42u) { vm_free(&vm); return 52; }
  if (rd32(&vm, G_PC) != 16u * 4u) { vm_free(&vm); return 53; }
  if (vm.rv_guest_stop_reason != RV_STOP_HALT) { vm_free(&vm); return 54; }

  vm_free(&vm);
  return 0;
}

static int case_memory(void) {
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 60;

  const uint32_t prog[] = {
    enc_op_imm(1, 0, 128, 0),             /* base */
    enc_op_imm(2, 0, -1, 0),              /* 0xff */
    enc_store(1, 2, 0, 0),                /* sb */
    enc_op_imm(3, 0, -128, 0),            /* 0x80 */
    enc_store(1, 3, 1, 0),                /* sb */
    enc_lui(4, 0x8u),                     /* 0x8000 */
    enc_op_imm(4, 4, 1, 0),               /* 0x8001 */
    enc_store(1, 4, 2, 1),                /* sh */
    enc_load(5, 1, 0, 0),                 /* lb  -> -1 */
    enc_load(6, 1, 0, 4),                 /* lbu -> 255 */
    enc_load(7, 1, 1, 0),                 /* lb  -> -128 */
    enc_load(8, 1, 1, 4),                 /* lbu -> 128 */
    enc_load(9, 1, 2, 1),                 /* lh  -> 0xffff8001 */
    enc_load(10, 1, 2, 5),                /* lhu -> 0x8001 */
    0u
  };

  int rc = run_program(&vm, prog, sizeof(prog) / sizeof(prog[0]), 64);
  if (rc != 0) { vm_free(&vm); return 61 + rc; }

  if (rd8(&vm, G_MEM_BASE + 128u * 8u + 0u * 8u) != 0xffu) { vm_free(&vm); return 70; }
  if (rd8(&vm, G_MEM_BASE + 128u * 8u + 1u * 8u) != 0x80u) { vm_free(&vm); return 71; }
  if (rd16(&vm, G_MEM_BASE + 128u * 8u + 2u * 8u) != 0x8001u) { vm_free(&vm); return 72; }
  if (reg32(&vm, 5) != 0xffffffffu) { vm_free(&vm); return 73; }
  if (reg32(&vm, 6) != 255u) { vm_free(&vm); return 74; }
  if (reg32(&vm, 7) != 0xffffff80u) { vm_free(&vm); return 75; }
  if (reg32(&vm, 8) != 128u) { vm_free(&vm); return 76; }
  if (reg32(&vm, 9) != 0xffff8001u) { vm_free(&vm); return 77; }
  if (reg32(&vm, 10) != 0x8001u) { vm_free(&vm); return 78; }
  if (vm.rv_guest_stop_reason != RV_STOP_HALT) { vm_free(&vm); return 79; }

  vm_free(&vm);
  return 0;
}

static int case_faults(void) {
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 80;

  const uint32_t prog_align[] = {
    enc_op_imm(1, 0, 33, 0),              /* misaligned for halfword */
    enc_load(2, 1, 0, 1),                 /* lh */
    0u
  };
  int rc = run_program(&vm, prog_align, sizeof(prog_align) / sizeof(prog_align[0]), 16);
  if (rc != 0) { vm_free(&vm); return 81 + rc; }
  if (vm.rv_guest_stop_reason != RV_STOP_ALIGN) { vm_free(&vm); return 90; }
  if (vm.rv_guest_steps != 2u) { vm_free(&vm); return 91; }
  vm_free(&vm);

  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 92;
  const uint32_t prog_bounds[] = {
    enc_lui(1, 0xffff0u),
    enc_load(2, 1, 0, 2),                 /* lw */
    0u
  };
  rc = run_program(&vm, prog_bounds, sizeof(prog_bounds) / sizeof(prog_bounds[0]), 16);
  if (rc != 0) { vm_free(&vm); return 93 + rc; }
  if (vm.rv_guest_stop_reason != RV_STOP_BOUNDS) { vm_free(&vm); return 100; }
  vm_free(&vm);

  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 101;
  const uint32_t prog_unsupported[] = { 0x0000000fu, 0u }; /* fence */
  rc = run_program(&vm, prog_unsupported, sizeof(prog_unsupported) / sizeof(prog_unsupported[0]), 16);
  if (rc != 0) { vm_free(&vm); return 102 + rc; }
  if (vm.rv_guest_stop_reason != RV_STOP_UNSUPPORTED) { vm_free(&vm); return 110; }
  if (vm.rv_guest_steps != 1u) { vm_free(&vm); return 111; }
  vm_free(&vm);

  return 0;
}

int main(void) {
  int rc = case_alu();
  if (rc != 0) return rc;
  rc = case_control();
  if (rc != 0) return rc;
  rc = case_memory();
  if (rc != 0) return rc;
  rc = case_faults();
  if (rc != 0) return rc;
  puts("OK rv32 stage3 rv32i runtime");
  return 0;
}
C

cc -O2 -I src/vm -o "$TMPDIR/rv32i_stage3_check" \
  "$TMPDIR/rv32i_stage3_check.c" src/vm/space.c src/vm/bitcpy.c

"$TMPDIR/rv32i_stage3_check"
