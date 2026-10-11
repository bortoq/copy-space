/* file: src/mkimage/std7_fixed/words_next.c
 * date: 2026-05-04
 * purpose: NEXT page builder extracted from words_core.c
 */
#include "words.h"
#include "words_int.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>

void write_next_page(vm_t *vm, bitaddr_t next_img,
                            bitaddr_t var_ip, bitaddr_t var_code, bitaddr_t var_next,
                            bitaddr_t const1_base)
{
  nop_fill_image(vm, next_img);

  const unsigned K=5;
  unsigned patch_slot = vm->processor_n - 2;
  unsigned load_slot  = vm->processor_n - 1;

  const unsigned S_PATCH_RCODE=1, S_RCODE=2, S_PATCH_RNEXT=3, S_SETBIT_K=4, S_RNEXT=5, S_IP_SET=6, S_PATCH_LOAD=7;

  bitaddr_t rcode_src_field = vm_proc_slot_field_ip(vm, S_RCODE, vm->off_src);
  bitaddr_t rnext_src_field = vm_proc_slot_field_ip(vm, S_RNEXT, vm->off_src);
  bitaddr_t load_src_field  = vm_proc_slot_field_ip(vm, load_slot, vm->off_src);

  vm_write_inst(vm, next_img + (bitaddr_t)S_PATCH_RCODE*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)rcode_src_field, .src=(uint64_t)var_ip });
  vm_write_inst(vm, next_img + (bitaddr_t)S_RCODE*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)var_code, .src=0 });

  vm_write_inst(vm, next_img + (bitaddr_t)S_PATCH_RNEXT*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)rnext_src_field, .src=(uint64_t)var_ip });

  unsigned j = vm->addr_bits - 1u - K;
  bitaddr_t rnext_src_bitK = rnext_src_field + (bitaddr_t)j;
  vm_write_inst(vm, next_img + (bitaddr_t)S_SETBIT_K*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)rnext_src_bitK, .src=(uint64_t)(const1_base+10) });

  vm_write_inst(vm, next_img + (bitaddr_t)S_RNEXT*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)var_next, .src=0 });

  vm_write_inst(vm, next_img + (bitaddr_t)S_IP_SET*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)var_ip, .src=(uint64_t)var_next });

  vm_write_inst(vm, next_img + (bitaddr_t)S_PATCH_LOAD*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)load_src_field, .src=(uint64_t)var_code });

  vm_write_inst(vm, next_img + (bitaddr_t)patch_slot*(bitaddr_t)vm->instr_bits, (vm_inst_t){0,0,0});
  vm_write_inst(vm, next_img + (bitaddr_t)load_slot*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->processor_bits, .dst=0, .src=0 });
}


