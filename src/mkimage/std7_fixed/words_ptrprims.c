/* file: src/mkimage/std7_fixed/words_ptrprims.c
 * purpose: 2b block-pointer primitives: LOAD24AP/LOAD24BP/STORE24RP
 */
#include "words.h"
#include "words_int.h"
#include <stdint.h>

void write_word_load24ap(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                         bitaddr_t VAR_A24, bitaddr_t VAR_AP)
{
  nop_fill_image(vm, img);

  const unsigned S_PATCH_SRC = 1;
  const unsigned S_LOAD      = 2;

  bitaddr_t load_src_field = vm_proc_slot_field_ip(vm, S_LOAD, vm->off_src);

  /* patch src-field of LOAD from VAR_AP */
  vm_write_inst(vm, img + (bitaddr_t)S_PATCH_SRC * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = vm->addr_bits,
                             .dst = (uint64_t)load_src_field,
                             .src = (uint64_t)VAR_AP });

  /* LOAD: A24 = *(AP) (24 bits) */
  vm_write_inst(vm, img + (bitaddr_t)S_LOAD * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = 24,
                             .dst = (uint64_t)VAR_A24,
                             .src = 0 });

  write_word_return_to_next(vm, img, next_img);
}

void write_word_load24bp(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                         bitaddr_t VAR_B24, bitaddr_t VAR_BP)
{
  nop_fill_image(vm, img);

  const unsigned S_PATCH_SRC = 1;
  const unsigned S_LOAD      = 2;

  bitaddr_t load_src_field = vm_proc_slot_field_ip(vm, S_LOAD, vm->off_src);

  vm_write_inst(vm, img + (bitaddr_t)S_PATCH_SRC * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = vm->addr_bits,
                             .dst = (uint64_t)load_src_field,
                             .src = (uint64_t)VAR_BP });

  vm_write_inst(vm, img + (bitaddr_t)S_LOAD * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = 24,
                             .dst = (uint64_t)VAR_B24,
                             .src = 0 });

  write_word_return_to_next(vm, img, next_img);
}

void write_word_store24rp(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                          bitaddr_t VAR_RP, bitaddr_t VAR_SUM24)
{
  nop_fill_image(vm, img);

  const unsigned S_PATCH_DST = 1;
  const unsigned S_STORE     = 2;

  bitaddr_t store_dst_field = vm_proc_slot_field_ip(vm, S_STORE, vm->off_dst);

  /* patch dst-field of STORE from VAR_RP */
  vm_write_inst(vm, img + (bitaddr_t)S_PATCH_DST * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = vm->addr_bits,
                             .dst = (uint64_t)store_dst_field,
                             .src = (uint64_t)VAR_RP });

  /* STORE: *(RP) = SUM24 (24 bits) */
  vm_write_inst(vm, img + (bitaddr_t)S_STORE * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = 24,
                             .dst = 0,
                             .src = (uint64_t)VAR_SUM24 });

  write_word_return_to_next(vm, img, next_img);
}
