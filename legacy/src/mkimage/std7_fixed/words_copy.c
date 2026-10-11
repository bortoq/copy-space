/* file: src/mkimage/std7_fixed/words_copy_mod.c
 * date: 2026-05-04
 * purpose: COPY word extracted from words_core.c
 */
#include "words.h"
#include "words_int.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>

void write_word_copy(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                            bitaddr_t var_n, bitaddr_t var_dst, bitaddr_t var_src)
{
  nop_fill_image(vm, img);
  const unsigned S_PATCH_N=1, S_PATCH_DST=2, S_PATCH_SRC=3, S_COPY=4;

  bitaddr_t copy_n   = vm_proc_slot_field_ip(vm, S_COPY, vm->off_n);
  bitaddr_t copy_dst = vm_proc_slot_field_ip(vm, S_COPY, vm->off_dst);
  bitaddr_t copy_src = vm_proc_slot_field_ip(vm, S_COPY, vm->off_src);

  vm_write_inst(vm, img + (bitaddr_t)S_PATCH_N*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)copy_n, .src=(uint64_t)var_n });
  vm_write_inst(vm, img + (bitaddr_t)S_PATCH_DST*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)copy_dst, .src=(uint64_t)var_dst });
  vm_write_inst(vm, img + (bitaddr_t)S_PATCH_SRC*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)copy_src, .src=(uint64_t)var_src });

  vm_write_inst(vm, img + (bitaddr_t)S_COPY*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=0, .dst=0, .src=0 });

  write_word_return_to_next(vm, img, next_img);
}


