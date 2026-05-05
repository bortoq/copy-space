/* file: src/mkimage/std7_fixed/words_eq24p.c
 * date: 2026-05-04
 * purpose: 2b microcode builder for EQ24P (pointer-based)
 */
#include "words.h"
#include "words_int.h"
#include <stdint.h>

void write_word_eq24p_micro(vm_t *vm,
                            bitaddr_t img, bitaddr_t chain_next,
                            unsigned off5,
                            int is_first, int is_last,
                            bitaddr_t VAR_AP, bitaddr_t VAR_BP,
                            bitaddr_t OFFTAB,
                            bitaddr_t BA, bitaddr_t BB, bitaddr_t BR,
                            bitaddr_t ACC_NEQ, bitaddr_t SCR,
                            bitaddr_t X0, bitaddr_t X1,
                            bitaddr_t CONST1, bitaddr_t CONST0,
                            bitaddr_t OUT_EQ)
{
  nop_fill_image(vm, img);
  unsigned last_slot = vm->processor_n - 1;
  unsigned s = 0;

  const unsigned A = vm->addr_bits;

  if (is_first) {
    vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                  (vm_inst_t){ .n=1, .dst=(uint64_t)ACC_NEQ, .src=(uint64_t)(CONST0+0) });
  }

  unsigned S_PATCH_A_PTR  = s++;
  unsigned S_PATCH_A_OFF5 = s++;
  unsigned S_READ_A       = s++;

  unsigned S_PATCH_B_PTR  = s++;
  unsigned S_PATCH_B_OFF5 = s++;
  unsigned S_READ_B       = s++;

  vm_write_inst(vm, img + (bitaddr_t)S_READ_A*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BA, .src=0 });
  vm_write_inst(vm, img + (bitaddr_t)S_READ_B*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BB, .src=0 });

  bitaddr_t readA_src_field = vm_proc_slot_field_ip(vm, S_READ_A, vm->off_src);
  bitaddr_t readB_src_field = vm_proc_slot_field_ip(vm, S_READ_B, vm->off_src);

  vm_write_inst(vm, img + (bitaddr_t)S_PATCH_A_PTR*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=(uint64_t)readA_src_field, .src=(uint64_t)VAR_AP });

  bitaddr_t offtab_src = OFFTAB + (bitaddr_t)off5 * 8u;
  bitaddr_t readA_low5 = readA_src_field + (bitaddr_t)(A - 5u);
  vm_write_inst(vm, img + (bitaddr_t)S_PATCH_A_OFF5*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=5, .dst=(uint64_t)readA_low5, .src=(uint64_t)offtab_src });

  vm_write_inst(vm, img + (bitaddr_t)S_PATCH_B_PTR*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=(uint64_t)readB_src_field, .src=(uint64_t)VAR_BP });

  bitaddr_t readB_low5 = readB_src_field + (bitaddr_t)(A - 5u);
  vm_write_inst(vm, img + (bitaddr_t)S_PATCH_B_OFF5*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=5, .dst=(uint64_t)readB_low5, .src=(uint64_t)offtab_src });

  s = S_READ_B + 1;

  emit_bxor(vm, img, &s, BA, BB, BR, X0, X1, CONST1, CONST0);
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)SCR, .src=(uint64_t)BR });

  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BA, .src=(uint64_t)ACC_NEQ });
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BB, .src=(uint64_t)SCR });

  emit_bor(vm, img, &s, BA, BB, BR, CONST1, CONST0);
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)ACC_NEQ, .src=(uint64_t)BR });

  if (is_last) {
    vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                  (vm_inst_t){ .n=1, .dst=(uint64_t)BA, .src=(uint64_t)ACC_NEQ });
    emit_bnot(vm, img, &s, BA, BR, CONST1, CONST0);
    vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                  (vm_inst_t){ .n=1, .dst=(uint64_t)OUT_EQ, .src=(uint64_t)BR });
  }

  while (s < last_slot)
    vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits, (vm_inst_t){0,0,0});

  write_chain_load(vm, img, chain_next);
}
