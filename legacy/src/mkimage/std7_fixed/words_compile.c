#include "words.h"
#include "words_int.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>

void write_word_compile_one(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                             bitaddr_t var_n, bitaddr_t var_token,
                             bitaddr_t var_free, bitaddr_t var_cur,
                             bitaddr_t var_nextfree, bitaddr_t var_prev_next_field,
                             bitaddr_t const1_base)
{
  nop_fill_image(vm, img);
  bitaddr_t A = vm->addr_bits;

  /* Slot layout:
   *   1: patch slot 2's src from [VAR_N] (indirect: read address stored in VAR_N)
   *   2: read token from [indirect addr] → VAR_TOKEN
   *   3: CUR = FREE (pop cell from free list)
   *   4: patch slot 5's src from CUR (read next_ptr from allocated cell)
   *   5: NEXTFREE = *(CUR) (read cell.next_ptr at offset 0)
   *   6: FREE = NEXTFREE
   *   7: patch slot 8's dst from PREV_NEXT_FLD (write link to prev cell)
   *   8: *(PREV_NEXT_FLD) = CUR (link prev to new cell)
   *   9: patch slot 10's dst from CUR (write token to cell.code_ptr at offset 0)
   *  10: *(CUR+0) = VAR_TOKEN (store token in cell.code_ptr)
   *  11: update PREV_NEXT_FLD = CUR (point to start of new cell)
   *  12: add 32 to PREV_NEXT_FLD (point to cell.next_ptr)
   *  13..: NOPs, then return
   */
  /*
   * KNOWN LIMITATION: FREE==0 (pool exhaustion) is NOT checked here.
   * The VM has no conditional branch instruction, so we cannot
   * branch on FREE==0 at runtime. If the free pool is exhausted,
   * slot 3 will copy 0 (nil address) into CUR, and subsequent
   * reads/writes will access address 0, leading to undefined behaviour.
   * This will be addressed in a future chain-load mechanism that can
   * check pool exhaustion via a dedicated page_pool_exhausted handler.
   * See "words_compile_pool_check.md" for the design.
   */
  unsigned s = 1;

  /* --- Slot 1: patch slot 2's src from VAR_N storage --- */
  bitaddr_t read_src = vm_proc_slot_field_ip(vm, 2, vm->off_src);
  vm_write_inst(vm, img + (bitaddr_t)s++ * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = A, .dst = (uint64_t)read_src,
                             .src = (uint64_t)var_n });

  /* --- Slot 2: read addr_bits from [patched src = addr stored in VAR_N] → VAR_TOKEN --- */
  vm_write_inst(vm, img + (bitaddr_t)s++ * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = A, .dst = (uint64_t)var_token,
                             .src = 0 });

  /* --- Slot 3: CUR = FREE (pop cell from free list) --- */
  vm_write_inst(vm, img + (bitaddr_t)s++ * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = A, .dst = (uint64_t)var_cur,
                             .src = (uint64_t)var_free });

  /* --- Slot 4: patch slot 5's src from CUR (read cell.next_ptr) --- */
  bitaddr_t rnext_src = vm_proc_slot_field_ip(vm, 5, vm->off_src);
  vm_write_inst(vm, img + (bitaddr_t)s++ * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = A, .dst = (uint64_t)rnext_src,
                             .src = (uint64_t)var_cur });

  /* --- Slot 5: NEXTFREE = *(CUR) (read cell.next_ptr from CUR) --- */
  vm_write_inst(vm, img + (bitaddr_t)s++ * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = A, .dst = (uint64_t)var_nextfree,
                             .src = 0 });

  /* --- Slot 6: FREE = NEXTFREE (update free list) --- */
  vm_write_inst(vm, img + (bitaddr_t)s++ * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = A, .dst = (uint64_t)var_free,
                             .src = (uint64_t)var_nextfree });

  /* --- Slot 7: patch slot 8's dst from PREV_NEXT_FLD --- */
  bitaddr_t link_dst = vm_proc_slot_field_ip(vm, 8, vm->off_dst);
  vm_write_inst(vm, img + (bitaddr_t)s++ * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = A, .dst = (uint64_t)link_dst,
                             .src = (uint64_t)var_prev_next_field });

  /* --- Slot 8: *(PREV_NEXT_FLD) = CUR (link prev cell to new cell) --- */
  vm_write_inst(vm, img + (bitaddr_t)s++ * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = A, .dst = 0,
                             .src = (uint64_t)var_cur });

  /* --- Slot 9: patch slot 10's dst from CUR (write token to cell.code_ptr) --- */
  bitaddr_t store_dst = vm_proc_slot_field_ip(vm, 10, vm->off_dst);
  vm_write_inst(vm, img + (bitaddr_t)s++ * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = A, .dst = (uint64_t)store_dst,
                             .src = (uint64_t)var_cur });

  /* --- Slot 10: write VAR_TOKEN to CUR->code_ptr (offset 0) --- */
  vm_write_inst(vm, img + (bitaddr_t)s++ * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = A, .dst = 0,
                             .src = (uint64_t)var_token });

  /* --- Slot 11: PREV_NEXT_FLD = CUR (update for next iteration) --- */
  vm_write_inst(vm, img + (bitaddr_t)s++ * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = A, .dst = (uint64_t)var_prev_next_field,
                             .src = (uint64_t)var_cur });

  /* --- Slot 12: add 32 to PREV_NEXT_FLD (point to new cell's next_ptr) --- */
  unsigned jj32 = A - 1u - 5;
  bitaddr_t prevnf_bit5 = var_prev_next_field + (bitaddr_t)jj32;
  vm_write_inst(vm, img + (bitaddr_t)s++ * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = 1, .dst = (uint64_t)prevnf_bit5,
                             .src = (uint64_t)(const1_base + 40) });

  write_word_return_to_next(vm, img, next_img);
}
