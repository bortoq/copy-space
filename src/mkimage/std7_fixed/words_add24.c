/* file: src/mkimage/std7_fixed/words_add24.c
 * date: 2026-05-04
 * purpose: 2a microcode builder: ADD24 (extracted from words_2a.c)
 */
#include "words.h"
#include "words_int.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>

void write_word_add24_micro(vm_t *vm,
                                   bitaddr_t img, bitaddr_t chain_next,
                                   bitaddr_t Abit, bitaddr_t Bbit, bitaddr_t Sbit,
                                   int is_first, int is_last,
                                   bitaddr_t OUT_COUT,
                                   bitaddr_t BA, bitaddr_t BB, bitaddr_t BC, bitaddr_t BR,
                                   bitaddr_t T0, bitaddr_t T1,
                                   bitaddr_t X0, bitaddr_t X1,
                                   bitaddr_t CONST1, bitaddr_t CONST0)
{
  nop_fill_image(vm, img);

  unsigned last = vm->processor_n - 1;
  unsigned s = 0;

  if (is_first) {
    // carry = 0
    vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                  (vm_inst_t){ .n=1, .dst=(uint64_t)BC, .src=(uint64_t)(CONST0+0) });
  }

  // BA = Abit; BB = Bbit
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BA, .src=(uint64_t)Abit });
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BB, .src=(uint64_t)Bbit });

  // t = A xor B -> BR; save to T0
  emit_bxor(vm, img, &s, BA, BB, BR, X0, X1, CONST1, CONST0);
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)T0, .src=(uint64_t)BR });

  // ab = A and B -> BR; save to T1
  emit_band(vm, img, &s, BA, BB, BR, CONST0);
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)T1, .src=(uint64_t)BR });

  // sum = t xor Cin -> BR
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BA, .src=(uint64_t)T0 });
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BB, .src=(uint64_t)BC });
  emit_bxor(vm, img, &s, BA, BB, BR, X0, X1, CONST1, CONST0);

  // store sum bit
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)Sbit, .src=(uint64_t)BR });

  // cin_t = Cin and t -> BR; save to T0
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BA, .src=(uint64_t)BC });
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BB, .src=(uint64_t)T0 });
  emit_band(vm, img, &s, BA, BB, BR, CONST0);
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)T0, .src=(uint64_t)BR });

  // cout = ab OR cin_t -> BR; store to BC
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BA, .src=(uint64_t)T1 });
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BB, .src=(uint64_t)T0 });
  emit_bor(vm, img, &s, BA, BB, BR, CONST1, CONST0);
  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)BC, .src=(uint64_t)BR });

  if (is_last) {
    // OUT_COUT = BC
    vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                  (vm_inst_t){ .n=1, .dst=(uint64_t)OUT_COUT, .src=(uint64_t)BC });
  }

  // Fill remaining slots (except last) with NOP
  while (s < last) {
    vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits, (vm_inst_t){0,0,0});
  }

  write_chain_load(vm, img, chain_next);
}




