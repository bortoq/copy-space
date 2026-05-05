/* file: src/mkimage/std7_fixed/words_helpers.c
 * date: 2026-05-04
 * purpose: helper functions extracted from words_all.c (page utils + boolean emitters)
 */
#include "words_int.h"
#include <stdint.h>

void nop_fill_image(vm_t *vm, bitaddr_t img_base) {
  vm_inst_t nop = (vm_inst_t){0,0,0};
  for (unsigned s=0; s<vm->processor_n; s++)
    vm_write_inst(vm, img_base + (bitaddr_t)s*(bitaddr_t)vm->instr_bits, nop);
}
void nop_fill_processor(vm_t *vm) {
  vm_inst_t nop = (vm_inst_t){0,0,0};
  for (unsigned s=0; s<vm->processor_n; s++)
    vm_write_inst(vm, vm_proc_slot_ip(vm, s), nop);
}
void write_chain_load(vm_t *vm, bitaddr_t img, bitaddr_t next_img) {
  unsigned last = vm->processor_n - 1;
  vm_write_inst(vm, img + (bitaddr_t)last*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=(uint64_t)vm->processor_bits, .dst=0, .src=(uint64_t)next_img });
}
void write_word_return_to_next(vm_t *vm, bitaddr_t word_img, bitaddr_t next_img) {
  write_chain_load(vm, word_img, next_img);
}

void write_cell(vm_t *vm, bitaddr_t cell_base, bitaddr_t code_ptr, bitaddr_t next_ptr) {
  vm_write_uint(vm, cell_base + 0,  vm->addr_bits, (uint64_t)code_ptr);
  vm_write_uint(vm, cell_base + 32, vm->addr_bits, (uint64_t)next_ptr);
}

/* ---------- helpers for boolean ops inside a page ---------- */
bitaddr_t n_lsb_of_slot(vm_t *vm, unsigned slot) {
  bitaddr_t n_field = vm_proc_slot_field_ip(vm, slot, vm->off_n);
  return n_field + (bitaddr_t)(vm->n_bits - 1u);
}

// R = (BA AND BB)
void emit_band(vm_t *vm, bitaddr_t img, unsigned *pslot,
                      bitaddr_t BA, bitaddr_t BB, bitaddr_t R,
                      bitaddr_t CONST0)
{
  unsigned s0 = (*pslot)++;
  unsigned sp = (*pslot)++;
  unsigned sc = (*pslot)++;

  vm_write_inst(vm, img + (bitaddr_t)s0*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)R, .src=(uint64_t)(CONST0+0) });

  bitaddr_t cond_n_lsb = n_lsb_of_slot(vm, sc);
  vm_write_inst(vm, img + (bitaddr_t)sp*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)cond_n_lsb, .src=(uint64_t)BA });

  vm_write_inst(vm, img + (bitaddr_t)sc*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=0, .dst=(uint64_t)R, .src=(uint64_t)BB });
}

// R = (BA OR BB)
void emit_bor(vm_t *vm, bitaddr_t img, unsigned *pslot,
                     bitaddr_t BA, bitaddr_t BB, bitaddr_t R,
                     bitaddr_t CONST1, bitaddr_t CONST0)
{
  unsigned s0 = (*pslot)++;
  unsigned spA = (*pslot)++;
  unsigned scA = (*pslot)++;
  unsigned spB = (*pslot)++;
  unsigned scB = (*pslot)++;

  vm_write_inst(vm, img + (bitaddr_t)s0*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)R, .src=(uint64_t)(CONST0+0) });

  bitaddr_t n_lsb_A = n_lsb_of_slot(vm, scA);
  vm_write_inst(vm, img + (bitaddr_t)spA*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)n_lsb_A, .src=(uint64_t)BA });
  vm_write_inst(vm, img + (bitaddr_t)scA*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=0, .dst=(uint64_t)R, .src=(uint64_t)(CONST1+0) });

  bitaddr_t n_lsb_B = n_lsb_of_slot(vm, scB);
  vm_write_inst(vm, img + (bitaddr_t)spB*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)n_lsb_B, .src=(uint64_t)BB });
  vm_write_inst(vm, img + (bitaddr_t)scB*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=0, .dst=(uint64_t)R, .src=(uint64_t)(CONST1+0) });
}

// R = (NOT BA)
void emit_bnot(vm_t *vm, bitaddr_t img, unsigned *pslot,
                      bitaddr_t BA, bitaddr_t R,
                      bitaddr_t CONST1, bitaddr_t CONST0)
{
  unsigned s1 = (*pslot)++;
  unsigned sp = (*pslot)++;
  unsigned sc = (*pslot)++;

  vm_write_inst(vm, img + (bitaddr_t)s1*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)R, .src=(uint64_t)(CONST1+0) });

  bitaddr_t cond_n_lsb = n_lsb_of_slot(vm, sc);
  vm_write_inst(vm, img + (bitaddr_t)sp*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)cond_n_lsb, .src=(uint64_t)BA });

  vm_write_inst(vm, img + (bitaddr_t)sc*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=0, .dst=(uint64_t)R, .src=(uint64_t)(CONST0+0) });
}

// R = (BA XOR BB) using internal temps X0/X1
void emit_bxor(vm_t *vm, bitaddr_t img, unsigned *pslot,
                      bitaddr_t BA, bitaddr_t BB, bitaddr_t R,
                      bitaddr_t X0, bitaddr_t X1,
                      bitaddr_t CONST1, bitaddr_t CONST0)
{
  // X0 = NOT BB
  unsigned s_x0_1 = (*pslot)++;
  unsigned s_x0_p = (*pslot)++;
  unsigned s_x0_c = (*pslot)++;

  vm_write_inst(vm, img + (bitaddr_t)s_x0_1*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)X0, .src=(uint64_t)(CONST1+0) });

  bitaddr_t n_lsb0 = n_lsb_of_slot(vm, s_x0_c);
  vm_write_inst(vm, img + (bitaddr_t)s_x0_p*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)n_lsb0, .src=(uint64_t)BB });

  vm_write_inst(vm, img + (bitaddr_t)s_x0_c*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=0, .dst=(uint64_t)X0, .src=(uint64_t)(CONST0+0) });

  // X1 = NOT BA
  unsigned s_x1_1 = (*pslot)++;
  unsigned s_x1_p = (*pslot)++;
  unsigned s_x1_c = (*pslot)++;

  vm_write_inst(vm, img + (bitaddr_t)s_x1_1*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)X1, .src=(uint64_t)(CONST1+0) });

  bitaddr_t n_lsb1 = n_lsb_of_slot(vm, s_x1_c);
  vm_write_inst(vm, img + (bitaddr_t)s_x1_p*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)n_lsb1, .src=(uint64_t)BA });

  vm_write_inst(vm, img + (bitaddr_t)s_x1_c*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=0, .dst=(uint64_t)X1, .src=(uint64_t)(CONST0+0) });

  // R = 0
  unsigned s_r0 = (*pslot)++;
  vm_write_inst(vm, img + (bitaddr_t)s_r0*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)R, .src=(uint64_t)(CONST0+0) });

  // if X1 (BA==0) then R = BB
  unsigned s_if1_p = (*pslot)++;
  unsigned s_if1_c = (*pslot)++;

  bitaddr_t n_lsb2 = n_lsb_of_slot(vm, s_if1_c);
  vm_write_inst(vm, img + (bitaddr_t)s_if1_p*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)n_lsb2, .src=(uint64_t)X1 });

  vm_write_inst(vm, img + (bitaddr_t)s_if1_c*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=0, .dst=(uint64_t)R, .src=(uint64_t)BB });

  // if BA then R = X0
  unsigned s_ifa_p = (*pslot)++;
  unsigned s_ifa_c = (*pslot)++;

  bitaddr_t n_lsb3 = n_lsb_of_slot(vm, s_ifa_c);
  vm_write_inst(vm, img + (bitaddr_t)s_ifa_p*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)n_lsb3, .src=(uint64_t)BA });

  vm_write_inst(vm, img + (bitaddr_t)s_ifa_c*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=0, .dst=(uint64_t)R, .src=(uint64_t)X0 });
}

