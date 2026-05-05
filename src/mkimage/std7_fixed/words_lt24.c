/* file: src/mkimage/std7_fixed/words_lt24.c
 * date: 2026-05-04
 * purpose: 2a microcode builder: LT24 (extracted from words_2a.c)
 */
#include "words.h"
#include "words_int.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>

void write_word_lt24_micro(vm_t *vm,
                                  bitaddr_t img, bitaddr_t chain_next,
                                  bitaddr_t Abit, bitaddr_t Bbit,
                                  int is_first, int is_last,
                                  bitaddr_t OUT_LT,
                                  bitaddr_t BA, bitaddr_t BB, bitaddr_t BR,
                                  bitaddr_t ST_EQ, bitaddr_t ST_LT,
                                  bitaddr_t SCR_DIFF,
                                  bitaddr_t X0, bitaddr_t X1,
                                  bitaddr_t CONST1, bitaddr_t CONST0)
{
  nop_fill_image(vm, img);
  unsigned last_slot = vm->processor_n - 1;
  unsigned s = 0;

  if (is_first) {
    // EQ=1, LT=0
    vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                  (vm_inst_t){ .n=1, .dst=(uint64_t)ST_EQ, .src=(uint64_t)(CONST1+0) });
    vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                  (vm_inst_t){ .n=1, .dst=(uint64_t)ST_LT, .src=(uint64_t)(CONST0+0) });
  }

  // BA=Abit, BB=Bbit
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BA, .src=(uint64_t)Abit });
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BB, .src=(uint64_t)Bbit });

  // diff = A xor B -> BR, save
  emit_bxor(vm, img, &s, BA, BB, BR, X0, X1, CONST1, CONST0);
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)SCR_DIFF, .src=(uint64_t)BR });

  // cond = (~A) & B
  emit_bnot(vm, img, &s, BA, BR, CONST1, CONST0); // BR = ~A
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BA, .src=(uint64_t)BR }); // BA=~A
  // BB already holds Bbit
  emit_band(vm, img, &s, BA, BB, BR, CONST0); // BR = cond

  // term = EQ & cond
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BA, .src=(uint64_t)ST_EQ });
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BB, .src=(uint64_t)BR });
  emit_band(vm, img, &s, BA, BB, BR, CONST0); // BR = term

  // LT = LT OR term
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BA, .src=(uint64_t)ST_LT });
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BB, .src=(uint64_t)BR });
  emit_bor(vm, img, &s, BA, BB, BR, CONST1, CONST0);
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)ST_LT, .src=(uint64_t)BR });

  // EQ = EQ & ~diff
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BA, .src=(uint64_t)SCR_DIFF });
  emit_bnot(vm, img, &s, BA, BR, CONST1, CONST0); // BR = ~diff
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BB, .src=(uint64_t)BR });
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BA, .src=(uint64_t)ST_EQ });
  emit_band(vm, img, &s, BA, BB, BR, CONST0);
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)ST_EQ, .src=(uint64_t)BR });

  if (is_last) {
    vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                  (vm_inst_t){ .n=1, .dst=(uint64_t)OUT_LT, .src=(uint64_t)ST_LT });
  }

  while (s < last_slot) {
    vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits, (vm_inst_t){0,0,0});
  }
  write_chain_load(vm, img, chain_next);
}


