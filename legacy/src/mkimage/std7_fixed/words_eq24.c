/* file: src/mkimage/std7_fixed/words_eq24.c
 * date: 2026-05-04
 * purpose: 2a microcode builder: EQ24 (extracted from words_2a.c)
 */
#include "words.h"
#include "words_int.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>

void write_word_eq24_micro(vm_t *vm,
                                  bitaddr_t img, bitaddr_t chain_next,
                                  bitaddr_t Abit, bitaddr_t Bbit,
                                  int is_first, int is_last,
                                  bitaddr_t OUT_EQ,
                                  bitaddr_t BA, bitaddr_t BB, bitaddr_t BR,
                                  bitaddr_t ACC_NEQ, bitaddr_t SCR,
                                  bitaddr_t X0, bitaddr_t X1,
                                  bitaddr_t CONST1, bitaddr_t CONST0)
{
  nop_fill_image(vm, img);
  unsigned last_slot = vm->processor_n - 1;
  unsigned s = 0;

  if (is_first) {
    // ACC_NEQ = 0
    vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                  (vm_inst_t){ .n=1, .dst=(uint64_t)ACC_NEQ, .src=(uint64_t)(CONST0+0) });
  }

  // BA=Abit, BB=Bbit
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BA, .src=(uint64_t)Abit });
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BB, .src=(uint64_t)Bbit });

  // diff = A xor B -> BR; SCR = diff
  emit_bxor(vm, img, &s, BA, BB, BR, X0, X1, CONST1, CONST0);
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)SCR, .src=(uint64_t)BR });

  // ACC_NEQ = ACC_NEQ OR diff
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BA, .src=(uint64_t)ACC_NEQ });
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BB, .src=(uint64_t)SCR });
  emit_bor(vm, img, &s, BA, BB, BR, CONST1, CONST0);
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)ACC_NEQ, .src=(uint64_t)BR });

  if (is_last) {
    // OUT_EQ = NOT ACC_NEQ
    vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                  (vm_inst_t){ .n=1, .dst=(uint64_t)BA, .src=(uint64_t)ACC_NEQ });
    emit_bnot(vm, img, &s, BA, BR, CONST1, CONST0);
    vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                  (vm_inst_t){ .n=1, .dst=(uint64_t)OUT_EQ, .src=(uint64_t)BR });
  }

  while (s < last_slot) {
    vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits, (vm_inst_t){0,0,0});
  }
  write_chain_load(vm, img, chain_next);
}




