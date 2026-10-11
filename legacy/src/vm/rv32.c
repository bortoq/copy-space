/* rv32.c — resident RV32I executor for Copy-Space */

#include "rv32.h"
#include <string.h>

enum {
  RV_TRACE_F_HAS_RD = 1u << 0,
  RV_TRACE_F_HAS_MEM_WRITE = 1u << 1,
  RV_TRACE_F_HAS_STOP_REASON = 1u << 2
};

static uint32_t rd_u32_le(const vm_t *vm, bitaddr_t bit_addr) {
  size_t b = (size_t)(bit_addr >> 3);
  return ((uint32_t)vm->space[b]) |
         ((uint32_t)vm->space[b + 1] << 8) |
         ((uint32_t)vm->space[b + 2] << 16) |
         ((uint32_t)vm->space[b + 3] << 24);
}

static uint16_t rd_u16_le(const vm_t *vm, bitaddr_t bit_addr) {
  size_t b = (size_t)(bit_addr >> 3);
  return (uint16_t)((uint16_t)vm->space[b] |
                    ((uint16_t)vm->space[b + 1] << 8));
}

static uint8_t rd_u8(const vm_t *vm, bitaddr_t bit_addr) {
  return vm->space[(size_t)(bit_addr >> 3)];
}

static void wr_u32_le(vm_t *vm, bitaddr_t bit_addr, uint32_t v) {
  size_t b = (size_t)(bit_addr >> 3);
  vm->space[b] = (uint8_t)(v & 0xffu);
  vm->space[b + 1] = (uint8_t)((v >> 8) & 0xffu);
  vm->space[b + 2] = (uint8_t)((v >> 16) & 0xffu);
  vm->space[b + 3] = (uint8_t)((v >> 24) & 0xffu);
}

static void wr_u16_le(vm_t *vm, bitaddr_t bit_addr, uint16_t v) {
  size_t b = (size_t)(bit_addr >> 3);
  vm->space[b] = (uint8_t)(v & 0xffu);
  vm->space[b + 1] = (uint8_t)((v >> 8) & 0xffu);
}

static void wr_u8(vm_t *vm, bitaddr_t bit_addr, uint8_t v) {
  vm->space[(size_t)(bit_addr >> 3)] = v;
}

static int32_t sext_imm12(uint32_t x) {
  return (int32_t)(x << 20) >> 20;
}

static int32_t sext_imm13(uint32_t x) {
  return (int32_t)(x << 19) >> 19;
}

static int32_t sext_imm21(uint32_t x) {
  return (int32_t)(x << 11) >> 11;
}

static int32_t sext_imm16(uint32_t x) {
  return (int32_t)(x << 16) >> 16;
}

static int32_t sext_imm8(uint32_t x) {
  return (int32_t)(x << 24) >> 24;
}

static uint32_t rv_trace_pack_meta(uint32_t opcode,
                                   uint32_t funct3,
                                   uint32_t funct7,
                                   uint32_t rd,
                                   uint32_t rs1,
                                   uint32_t rs2) {
  return (opcode & 0x7fu) |
         ((funct3 & 0x7u) << 7) |
         ((funct7 & 0x7fu) << 10) |
         ((rd & 0x1fu) << 17) |
         ((rs1 & 0x1fu) << 22) |
         ((rs2 & 0x1fu) << 27);
}

static uint32_t rv_trace_pack_flags(unsigned has_rd,
                                    unsigned has_mem_write,
                                    unsigned has_stop_reason,
                                    unsigned mem_width_bytes,
                                    unsigned stop_reason) {
  return (has_rd ? RV_TRACE_F_HAS_RD : 0u) |
         (has_mem_write ? RV_TRACE_F_HAS_MEM_WRITE : 0u) |
         (has_stop_reason ? RV_TRACE_F_HAS_STOP_REASON : 0u) |
         ((mem_width_bytes & 0xffu) << 8) |
         ((stop_reason & 0xffu) << 16);
}

void rv32_trace_reset(vm_t *vm) {
  vm->rv_trace_count = 0;
  vm->rv_trace_dropped = 0;
}

static void rv32_trace_append(vm_t *vm, rv_trace_record_t rec) {
  if (vm->rv_trace_count < vm->rv_trace_capacity) {
    vm->rv_trace_records[vm->rv_trace_count++] = rec;
  } else {
    vm->rv_trace_dropped++;
  }
}

static void rv32_guest_stop(vm_t *vm, rv_stop_reason_t reason) {
  vm->rv_guest_stop_reason = reason;
  vm_bit_set(vm, vm->mmio.halt, 1);
  vm->rv_guest_running = 0;
}

static void rv32_guest_commit(vm_t *vm, uint32_t next_pc) {
  const bitaddr_t G_PC = 0x001000ULL;
  const bitaddr_t G_REG_BASE = 0x001200ULL;

  wr_u32_le(vm, G_PC, next_pc);
  wr_u32_le(vm, G_REG_BASE + 0u, 0u);
}

static int rv32_addr_check(vm_t *vm,
                           uint32_t addr,
                           unsigned width_bytes,
                           unsigned align_bytes,
                           bitaddr_t *guest_addr_out) {
  bitaddr_t guest_addr = 0x002000ULL + (bitaddr_t)addr * 8u;
  if (align_bytes > 1u && (addr & (uint32_t)(align_bytes - 1u)) != 0u) {
    rv32_guest_stop(vm, RV_STOP_ALIGN);
    return -1;
  }
  if (guest_addr + (bitaddr_t)width_bytes * 8u > vm->space_bits) {
    rv32_guest_stop(vm, RV_STOP_BOUNDS);
    return -1;
  }
  *guest_addr_out = guest_addr;
  return 0;
}

int rv32_guest_step(vm_t *vm) {
  const bitaddr_t G_PC = 0x001000ULL;
  const bitaddr_t G_REG_BASE = 0x001200ULL;
  uint32_t pc = rd_u32_le(vm, G_PC);
  bitaddr_t insn_addr = 0x002000ULL + (bitaddr_t)pc * 8u;
  rv_trace_record_t tr;
  memset(&tr, 0, sizeof(tr));
  tr.pc = pc;
  tr.step = (uint32_t)vm->rv_guest_steps;
  if (insn_addr + 32u > vm->space_bits) {
    tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 0u, RV_STOP_BOUNDS);
    rv32_trace_append(vm, tr);
    rv32_guest_stop(vm, RV_STOP_BOUNDS);
    return 0;
  }

  uint32_t insn = rd_u32_le(vm, insn_addr);
  tr.instr = insn;
  if (insn == 0u) {
    tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 0u, RV_STOP_HALT);
    rv32_trace_append(vm, tr);
    rv32_guest_stop(vm, RV_STOP_HALT);
    return 0;
  }

  vm->rv_guest_steps++;
  tr.step = (uint32_t)vm->rv_guest_steps;

  uint32_t opcode = insn & 0x7fu;
  if (opcode == 0x37u) { /* LUI */
    uint32_t rd = (insn >> 7) & 0x1fu;
    uint32_t imm = insn & 0xfffff000u;
    tr.imm = imm;
    tr.meta = rv_trace_pack_meta(opcode, 0u, 0u, rd, 0u, 0u);
    if (rd != 0u) wr_u32_le(vm, G_REG_BASE + (bitaddr_t)rd * 32u, imm);
    tr.rd_value = imm;
    tr.flags = rv_trace_pack_flags(rd != 0u, 0u, 0u, 0u, 0u);
    rv32_trace_append(vm, tr);
    rv32_guest_commit(vm, pc + 4u);
    return 0;
  }
  if (opcode == 0x17u) { /* AUIPC */
    uint32_t rd = (insn >> 7) & 0x1fu;
    uint32_t imm = insn & 0xfffff000u;
    uint32_t rdv = pc + imm;
    tr.imm = imm;
    tr.meta = rv_trace_pack_meta(opcode, 0u, 0u, rd, 0u, 0u);
    if (rd != 0u) wr_u32_le(vm, G_REG_BASE + (bitaddr_t)rd * 32u, rdv);
    tr.rd_value = rdv;
    tr.flags = rv_trace_pack_flags(rd != 0u, 0u, 0u, 0u, 0u);
    rv32_trace_append(vm, tr);
    rv32_guest_commit(vm, pc + 4u);
    return 0;
  }
  if (opcode == 0x13u) { /* OP-IMM */
    uint32_t funct3 = (insn >> 12) & 0x7u;
    uint32_t rd = (insn >> 7) & 0x1fu;
    uint32_t rs1 = (insn >> 15) & 0x1fu;
    int32_t imm = sext_imm12(insn >> 20);
    uint32_t funct7 = (insn >> 25) & 0x7fu;
    uint32_t rs1v = rd_u32_le(vm, G_REG_BASE + (bitaddr_t)rs1 * 32u);
    uint32_t rdv = 0u;
    tr.imm = (uint32_t)imm;
    tr.meta = rv_trace_pack_meta(opcode, funct3, funct7, rd, rs1, 0u);

    if (funct3 == 0u) rdv = (uint32_t)((int32_t)rs1v + imm);
    else if (funct3 == 2u) rdv = ((int32_t)rs1v < imm) ? 1u : 0u;
    else if (funct3 == 3u) rdv = (rs1v < (uint32_t)imm) ? 1u : 0u;
    else if (funct3 == 4u) rdv = rs1v ^ (uint32_t)imm;
    else if (funct3 == 6u) rdv = rs1v | (uint32_t)imm;
    else if (funct3 == 7u) rdv = rs1v & (uint32_t)imm;
    else if (funct3 == 1u) {
      if ((insn >> 25) != 0u) {
        tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 0u, RV_STOP_UNSUPPORTED);
        rv32_trace_append(vm, tr);
        rv32_guest_stop(vm, RV_STOP_UNSUPPORTED);
        return 0;
      }
      rdv = rs1v << ((insn >> 20) & 0x1fu);
    } else if (funct3 == 5u) {
      uint32_t shamt = (insn >> 20) & 0x1fu;
      if (funct7 == 0x00u) rdv = rs1v >> shamt;
      else if (funct7 == 0x20u) rdv = (uint32_t)((int32_t)rs1v >> shamt);
      else {
        tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 0u, RV_STOP_UNSUPPORTED);
        rv32_trace_append(vm, tr);
        rv32_guest_stop(vm, RV_STOP_UNSUPPORTED);
        return 0;
      }
    } else {
      tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 0u, RV_STOP_UNSUPPORTED);
      rv32_trace_append(vm, tr);
      rv32_guest_stop(vm, RV_STOP_UNSUPPORTED);
      return 0;
    }

    if (rd != 0u) wr_u32_le(vm, G_REG_BASE + (bitaddr_t)rd * 32u, rdv);
    tr.rd_value = rdv;
    tr.flags = rv_trace_pack_flags(rd != 0u, 0u, 0u, 0u, 0u);
    rv32_trace_append(vm, tr);
    rv32_guest_commit(vm, pc + 4u);
    return 0;
  }
  if (opcode == 0x33u) { /* OP */
    uint32_t funct3 = (insn >> 12) & 0x7u;
    uint32_t funct7 = (insn >> 25) & 0x7fu;
    uint32_t rd = (insn >> 7) & 0x1fu;
    uint32_t rs1 = (insn >> 15) & 0x1fu;
    uint32_t rs2 = (insn >> 20) & 0x1fu;
    uint32_t a = rd_u32_le(vm, G_REG_BASE + (bitaddr_t)rs1 * 32u);
    uint32_t b = rd_u32_le(vm, G_REG_BASE + (bitaddr_t)rs2 * 32u);
    uint32_t rdv = 0u;
    tr.meta = rv_trace_pack_meta(opcode, funct3, funct7, rd, rs1, rs2);

    if (funct7 == 0x00u && funct3 == 0u) rdv = a + b;
    else if (funct7 == 0x20u && funct3 == 0u) rdv = a - b;
    else if (funct7 == 0x00u && funct3 == 1u) rdv = a << (b & 0x1fu);
    else if (funct7 == 0x00u && funct3 == 2u) rdv = ((int32_t)a < (int32_t)b) ? 1u : 0u;
    else if (funct7 == 0x00u && funct3 == 3u) rdv = (a < b) ? 1u : 0u;
    else if (funct7 == 0x00u && funct3 == 4u) rdv = a ^ b;
    else if (funct7 == 0x00u && funct3 == 5u) rdv = a >> (b & 0x1fu);
    else if (funct7 == 0x20u && funct3 == 5u) rdv = (uint32_t)((int32_t)a >> (b & 0x1fu));
    else if (funct7 == 0x00u && funct3 == 6u) rdv = a | b;
    else if (funct7 == 0x00u && funct3 == 7u) rdv = a & b;
    else {
      tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 0u, RV_STOP_UNSUPPORTED);
      rv32_trace_append(vm, tr);
      rv32_guest_stop(vm, RV_STOP_UNSUPPORTED);
      return 0;
    }

    if (rd != 0u) wr_u32_le(vm, G_REG_BASE + (bitaddr_t)rd * 32u, rdv);
    tr.rd_value = rdv;
    tr.flags = rv_trace_pack_flags(rd != 0u, 0u, 0u, 0u, 0u);
    rv32_trace_append(vm, tr);
    rv32_guest_commit(vm, pc + 4u);
    return 0;
  }
  if (opcode == 0x03u) { /* LOAD */
    uint32_t funct3 = (insn >> 12) & 0x7u;
    uint32_t rd = (insn >> 7) & 0x1fu;
    uint32_t rs1 = (insn >> 15) & 0x1fu;
    int32_t imm = sext_imm12(insn >> 20);
    uint32_t base = rd_u32_le(vm, G_REG_BASE + (bitaddr_t)rs1 * 32u);
    uint32_t addr = (uint32_t)((int32_t)base + imm);
    bitaddr_t ga = 0;
    uint32_t v = 0u;
    tr.imm = (uint32_t)imm;
    tr.meta = rv_trace_pack_meta(opcode, funct3, 0u, rd, rs1, 0u);

    if (funct3 == 0u) {
      if (rv32_addr_check(vm, addr, 1u, 1u, &ga) != 0) {
        tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 1u, (unsigned)vm->rv_guest_stop_reason);
        rv32_trace_append(vm, tr);
        return 0;
      }
      v = (uint32_t)sext_imm8(rd_u8(vm, ga));
    } else if (funct3 == 1u) {
      if (rv32_addr_check(vm, addr, 2u, 2u, &ga) != 0) {
        tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 2u, (unsigned)vm->rv_guest_stop_reason);
        rv32_trace_append(vm, tr);
        return 0;
      }
      v = (uint32_t)sext_imm16(rd_u16_le(vm, ga));
    } else if (funct3 == 2u) {
      if (rv32_addr_check(vm, addr, 4u, 4u, &ga) != 0) {
        tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 4u, (unsigned)vm->rv_guest_stop_reason);
        rv32_trace_append(vm, tr);
        return 0;
      }
      v = rd_u32_le(vm, ga);
    } else if (funct3 == 4u) {
      if (rv32_addr_check(vm, addr, 1u, 1u, &ga) != 0) {
        tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 1u, (unsigned)vm->rv_guest_stop_reason);
        rv32_trace_append(vm, tr);
        return 0;
      }
      v = rd_u8(vm, ga);
    } else if (funct3 == 5u) {
      if (rv32_addr_check(vm, addr, 2u, 2u, &ga) != 0) {
        tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 2u, (unsigned)vm->rv_guest_stop_reason);
        rv32_trace_append(vm, tr);
        return 0;
      }
      v = rd_u16_le(vm, ga);
    } else {
      tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 0u, RV_STOP_UNSUPPORTED);
      rv32_trace_append(vm, tr);
      rv32_guest_stop(vm, RV_STOP_UNSUPPORTED);
      return 0;
    }

    if (rd != 0u) wr_u32_le(vm, G_REG_BASE + (bitaddr_t)rd * 32u, v);
    tr.rd_value = v;
    tr.flags = rv_trace_pack_flags(rd != 0u, 0u, 0u,
                                   (funct3 == 1u || funct3 == 5u) ? 2u :
                                   (funct3 == 2u ? 4u : 1u),
                                   0u);
    rv32_trace_append(vm, tr);
    rv32_guest_commit(vm, pc + 4u);
    return 0;
  }
  if (opcode == 0x23u) { /* STORE */
    uint32_t funct3 = (insn >> 12) & 0x7u;
    uint32_t rs1 = (insn >> 15) & 0x1fu;
    uint32_t rs2 = (insn >> 20) & 0x1fu;
    uint32_t imm_u = ((insn >> 7) & 0x1fu) | (((insn >> 25) & 0x7fu) << 5);
    int32_t imm = sext_imm12(imm_u);
    uint32_t base = rd_u32_le(vm, G_REG_BASE + (bitaddr_t)rs1 * 32u);
    uint32_t addr = (uint32_t)((int32_t)base + imm);
    bitaddr_t ga = 0;
    uint32_t v = rd_u32_le(vm, G_REG_BASE + (bitaddr_t)rs2 * 32u);
    unsigned mem_width_bytes = 0u;
    tr.imm = (uint32_t)imm;
    tr.meta = rv_trace_pack_meta(opcode, funct3, 0u, 0u, rs1, rs2);

    if (funct3 == 0u) {
      if (rv32_addr_check(vm, addr, 1u, 1u, &ga) != 0) {
        tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 1u, (unsigned)vm->rv_guest_stop_reason);
        rv32_trace_append(vm, tr);
        return 0;
      }
      wr_u8(vm, ga, (uint8_t)(v & 0xffu));
      mem_width_bytes = 1u;
    } else if (funct3 == 1u) {
      if (rv32_addr_check(vm, addr, 2u, 2u, &ga) != 0) {
        tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 2u, (unsigned)vm->rv_guest_stop_reason);
        rv32_trace_append(vm, tr);
        return 0;
      }
      wr_u16_le(vm, ga, (uint16_t)(v & 0xffffu));
      mem_width_bytes = 2u;
    } else if (funct3 == 2u) {
      if (rv32_addr_check(vm, addr, 4u, 4u, &ga) != 0) {
        tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 4u, (unsigned)vm->rv_guest_stop_reason);
        rv32_trace_append(vm, tr);
        return 0;
      }
      wr_u32_le(vm, ga, v);
      mem_width_bytes = 4u;
    } else {
      tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 0u, RV_STOP_UNSUPPORTED);
      rv32_trace_append(vm, tr);
      rv32_guest_stop(vm, RV_STOP_UNSUPPORTED);
      return 0;
    }

    tr.mem_addr = addr;
    tr.mem_value = v;
    tr.flags = rv_trace_pack_flags(0u, 1u, 0u, mem_width_bytes, 0u);
    rv32_trace_append(vm, tr);
    rv32_guest_commit(vm, pc + 4u);
    return 0;
  }
  if (opcode == 0x63u) { /* BRANCH */
    uint32_t funct3 = (insn >> 12) & 0x7u;
    uint32_t rs1 = (insn >> 15) & 0x1fu;
    uint32_t rs2 = (insn >> 20) & 0x1fu;
    uint32_t imm_u = (((insn >> 31) & 0x1u) << 12) |
                     (((insn >> 7) & 0x1u) << 11) |
                     (((insn >> 25) & 0x3fu) << 5) |
                     (((insn >> 8) & 0xfu) << 1);
    int32_t imm = sext_imm13(imm_u);
    uint32_t a = rd_u32_le(vm, G_REG_BASE + (bitaddr_t)rs1 * 32u);
    uint32_t b = rd_u32_le(vm, G_REG_BASE + (bitaddr_t)rs2 * 32u);
    int take = 0;
    tr.imm = (uint32_t)imm;
    tr.meta = rv_trace_pack_meta(opcode, funct3, 0u, 0u, rs1, rs2);
    if (funct3 == 0u) take = (a == b);
    else if (funct3 == 1u) take = (a != b);
    else if (funct3 == 4u) take = ((int32_t)a < (int32_t)b);
    else if (funct3 == 5u) take = ((int32_t)a >= (int32_t)b);
    else if (funct3 == 6u) take = (a < b);
    else if (funct3 == 7u) take = (a >= b);
    else {
      tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 0u, RV_STOP_UNSUPPORTED);
      rv32_trace_append(vm, tr);
      rv32_guest_stop(vm, RV_STOP_UNSUPPORTED);
      return 0;
    }
    tr.flags = rv_trace_pack_flags(0u, 0u, 0u, 0u, 0u);
    rv32_trace_append(vm, tr);
    rv32_guest_commit(vm, take ? (uint32_t)((int32_t)pc + imm) : (pc + 4u));
    return 0;
  }
  if (opcode == 0x6fu) { /* JAL */
    uint32_t rd = (insn >> 7) & 0x1fu;
    uint32_t imm_u = (((insn >> 31) & 0x1u) << 20) |
                     (((insn >> 12) & 0xffu) << 12) |
                     (((insn >> 20) & 0x1u) << 11) |
                     (((insn >> 21) & 0x3ffu) << 1);
    int32_t imm = sext_imm21(imm_u);
    uint32_t next = pc + 4u;
    tr.imm = (uint32_t)imm;
    tr.meta = rv_trace_pack_meta(opcode, 0u, 0u, rd, 0u, 0u);
    pc = (uint32_t)((int32_t)pc + imm);
    if (rd != 0u) wr_u32_le(vm, G_REG_BASE + (bitaddr_t)rd * 32u, next);
    tr.rd_value = next;
    tr.flags = rv_trace_pack_flags(rd != 0u, 0u, 0u, 0u, 0u);
    rv32_trace_append(vm, tr);
    rv32_guest_commit(vm, pc);
    return 0;
  }
  if (opcode == 0x67u) { /* JALR */
    uint32_t rd = (insn >> 7) & 0x1fu;
    uint32_t rs1 = (insn >> 15) & 0x1fu;
    uint32_t funct3 = (insn >> 12) & 0x7u;
    int32_t imm = sext_imm12(insn >> 20);
    uint32_t base = rd_u32_le(vm, G_REG_BASE + (bitaddr_t)rs1 * 32u);
    uint32_t next = pc + 4u;
    uint32_t target = (uint32_t)(((int32_t)base + imm) & ~1u);
    tr.imm = (uint32_t)imm;
    tr.meta = rv_trace_pack_meta(opcode, funct3, 0u, rd, rs1, 0u);
    if (funct3 != 0u) {
      tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 0u, RV_STOP_UNSUPPORTED);
      rv32_trace_append(vm, tr);
      rv32_guest_stop(vm, RV_STOP_UNSUPPORTED);
      return 0;
    }
    if (rd != 0u) wr_u32_le(vm, G_REG_BASE + (bitaddr_t)rd * 32u, next);
    tr.rd_value = next;
    tr.flags = rv_trace_pack_flags(rd != 0u, 0u, 0u, 0u, 0u);
    rv32_trace_append(vm, tr);
    rv32_guest_commit(vm, target);
    return 0;
  }

  tr.flags = rv_trace_pack_flags(0u, 0u, 1u, 0u, RV_STOP_UNSUPPORTED);
  rv32_trace_append(vm, tr);
  rv32_guest_stop(vm, RV_STOP_UNSUPPORTED);
  return 0;
}
