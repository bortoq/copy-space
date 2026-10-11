/* file: src/mkimage/std7_fixed/words_literals.c
 * date: 2026-05-04
 * purpose: literal-related words extracted from words_core.c
 */
#include "words.h"
#include "words_int.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>

void write_word_lit_generic(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                                   bitaddr_t var_ip, bitaddr_t var_x,
                                   bitaddr_t const1_base)
{
  nop_fill_image(vm, img);
  const unsigned K=5;
  const unsigned S_PATCH_RCODE=1, S_RCODE=2, S_PATCH_RNEXT=3, S_SETBIT_K=4, S_RNEXT=5;

  bitaddr_t rcode_src = vm_proc_slot_field_ip(vm, S_RCODE, vm->off_src);
  bitaddr_t rnext_src = vm_proc_slot_field_ip(vm, S_RNEXT, vm->off_src);

  vm_write_inst(vm, img + (bitaddr_t)S_PATCH_RCODE*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)rcode_src, .src=(uint64_t)var_ip });
  vm_write_inst(vm, img + (bitaddr_t)S_RCODE*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)var_x, .src=0 });

  vm_write_inst(vm, img + (bitaddr_t)S_PATCH_RNEXT*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)rnext_src, .src=(uint64_t)var_ip });

  unsigned j = vm->addr_bits - 1u - K;
  bitaddr_t rnext_src_bitK = rnext_src + (bitaddr_t)j;
  vm_write_inst(vm, img + (bitaddr_t)S_SETBIT_K*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)rnext_src_bitK, .src=(uint64_t)(const1_base+60) });

  vm_write_inst(vm, img + (bitaddr_t)S_RNEXT*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)var_ip, .src=0 });

  write_word_return_to_next(vm, img, next_img);
}



void write_word_litip(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                             bitaddr_t var_ip, bitaddr_t var_src,
                             bitaddr_t const1_base)
{
  nop_fill_image(vm, img);
  const unsigned K=5;
  const unsigned S_SRC_EQ_IP=1, S_PATCH_RNEXT=2, S_SETBIT_K=3, S_RNEXT=4;

  vm_write_inst(vm, img + (bitaddr_t)S_SRC_EQ_IP*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)var_src, .src=(uint64_t)var_ip });

  bitaddr_t rnext_src = vm_proc_slot_field_ip(vm, S_RNEXT, vm->off_src);
  vm_write_inst(vm, img + (bitaddr_t)S_PATCH_RNEXT*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)rnext_src, .src=(uint64_t)var_ip });

  unsigned j = vm->addr_bits - 1u - K;
  bitaddr_t rnext_src_bitK = rnext_src + (bitaddr_t)j;
  vm_write_inst(vm, img + (bitaddr_t)S_SETBIT_K*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)rnext_src_bitK, .src=(uint64_t)(const1_base+61) });

  vm_write_inst(vm, img + (bitaddr_t)S_RNEXT*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)var_ip, .src=0 });

  write_word_return_to_next(vm, img, next_img);
}


