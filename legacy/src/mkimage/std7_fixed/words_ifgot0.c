/* file: src/mkimage/std7_fixed/words_ifgot0.c
 * date: 2026-05-04
 * purpose: IFGOT0 word extracted from words_core.c
 */
#include "words.h"
#include "words_int.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>

void write_word_ifgot0(vm_t *vm,
                              bitaddr_t img, bitaddr_t next_img,
                              bitaddr_t var_ip,
                              bitaddr_t var_flag, bitaddr_t var_z,
                              bitaddr_t const1_base, bitaddr_t const0_base,
                              unsigned bsel)
{
  nop_fill_image(vm, img);

  const bitaddr_t A = vm->addr_bits;
  unsigned s = 1;

  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)var_flag, .src=(uint64_t)(const0_base+0) });

  for (unsigned i = 0; i < A; i++) {
    unsigned patch_slot = s;
    unsigned setacc_slot = s + 1;

    bitaddr_t setacc_n_field = vm_proc_slot_field_ip(vm, setacc_slot, vm->off_n);
    bitaddr_t setacc_n_lsb   = setacc_n_field + (bitaddr_t)(A - 1u);

    bitaddr_t got_bit = vm->mmio.in_got + (bitaddr_t)i;

    vm_write_inst(vm, img + (bitaddr_t)patch_slot*(bitaddr_t)vm->instr_bits,
                  (vm_inst_t){ .n=1, .dst=(uint64_t)setacc_n_lsb, .src=(uint64_t)got_bit });

    vm_write_inst(vm, img + (bitaddr_t)setacc_slot*(bitaddr_t)vm->instr_bits,
                  (vm_inst_t){ .n=0, .dst=(uint64_t)var_flag, .src=(uint64_t)(const1_base+1) });

    s += 2;
  }

  vm_write_inst(vm, img + (bitaddr_t)s++*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)var_z, .src=(uint64_t)(const1_base+2) });

  unsigned patch_clr = s;
  unsigned clr_slot  = s + 1;

  bitaddr_t clr_n_field = vm_proc_slot_field_ip(vm, clr_slot, vm->off_n);
  bitaddr_t clr_n_lsb   = clr_n_field + (bitaddr_t)(A - 1u);

  vm_write_inst(vm, img + (bitaddr_t)patch_clr*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)clr_n_lsb, .src=(uint64_t)var_flag });

  vm_write_inst(vm, img + (bitaddr_t)clr_slot*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=0, .dst=(uint64_t)var_z, .src=(uint64_t)(const0_base+1) });

  s += 2;

  unsigned off = vm->addr_bits - 1u - bsel;

  const unsigned S_PATCH_DST = s++;
  const unsigned S_SET0 = s++, S_SET1 = s++, S_SET2 = s++, S_SET3 = s++;
  const unsigned S_COPYBIT = s++;

  bitaddr_t copybit_dst_field = vm_proc_slot_field_ip(vm, S_COPYBIT, vm->off_dst);

  vm_write_inst(vm, img + (bitaddr_t)S_PATCH_DST*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=(uint64_t)copybit_dst_field, .src=(uint64_t)var_ip });

  unsigned slots4[4] = { S_SET0, S_SET1, S_SET2, S_SET3 };
  unsigned si=0;
  for (unsigned p=0; p<6 && si<4; p++) if (off & (1u<<p)) {
    unsigned j = A - 1u - p;
    bitaddr_t dstbit = copybit_dst_field + (bitaddr_t)j;
    vm_write_inst(vm, img + (bitaddr_t)slots4[si++]*(bitaddr_t)vm->instr_bits,
                  (vm_inst_t){ .n=1, .dst=(uint64_t)dstbit, .src=(uint64_t)(const1_base+100+p) });
  }
  while (si<4) vm_write_inst(vm, img + (bitaddr_t)slots4[si++]*(bitaddr_t)vm->instr_bits, (vm_inst_t){0,0,0});

  vm_write_inst(vm, img + (bitaddr_t)S_COPYBIT*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=0, .src=(uint64_t)var_z });

  write_word_return_to_next(vm, img, next_img);
}


