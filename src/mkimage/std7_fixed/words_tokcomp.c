/* file: src/mkimage/std7_fixed/words_tokcomp.c
 * date: 2026-05-04
 * purpose: token compiler pages (DO/END/BRANCH) extracted from words_core.c
 */
#include "words.h"
#include "words_int.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>

void write_page_branch(vm_t *vm, bitaddr_t img_branch, bitaddr_t do_base, unsigned bsel) {
  nop_fill_image(vm, img_branch);
  unsigned patch_slot = vm->processor_n - 2;
  unsigned load_slot  = vm->processor_n - 1;
  bitaddr_t slot0_dst = vm_proc_slot_field_ip(vm, 0, vm->off_dst);
  bitaddr_t load_src  = vm_proc_slot_field_ip(vm, load_slot, vm->off_src);
  unsigned j = vm->addr_bits - 1u - bsel;
  bitaddr_t slot0_dst_bit = slot0_dst + (bitaddr_t)j;

  vm_write_inst(vm, img_branch + 0, (vm_inst_t){ .n=0, .dst=(uint64_t)do_base, .src=0 });
  vm_write_inst(vm, img_branch + 1u*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)slot0_dst_bit, .src=(uint64_t)vm->mmio.in_eof });

  vm_write_inst(vm, img_branch + (bitaddr_t)patch_slot*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)load_src, .src=(uint64_t)slot0_dst });
  vm_write_inst(vm, img_branch + (bitaddr_t)load_slot*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->processor_bits, .dst=0, .src=0 });
}



void write_page_do(vm_t *vm, bitaddr_t img_do, bitaddr_t img_branch,
                          bitaddr_t var_free, bitaddr_t var_cur, bitaddr_t var_nextfree,
                          bitaddr_t var_prev_next_field, bitaddr_t var_token,
                          bitaddr_t const1_base)
{
  nop_fill_image(vm, img_do);
  bitaddr_t A = vm->addr_bits;

  unsigned patch_slot = vm->processor_n - 2;
  unsigned load_slot  = vm->processor_n - 1;

  const unsigned S_CUR_EQ_FREE=1, S_PATCH_READNF=2, S_READNF=3, S_FREE_EQ_NF=4;
  const unsigned S_PATCH_PREV_DST=5, S_PREV_WRITE=6;
  const unsigned S_PATCH_STORE_DST=7, S_STORE_CODE=8;
  const unsigned S_PREVNF_SET=9, S_PREVNF_BIT5=10;
  const unsigned S_INREQ=11;

  vm_write_inst(vm, img_do + 0, (vm_inst_t){ .n=0, .dst=(uint64_t)img_branch, .src=0 });

  vm_write_inst(vm, img_do + (bitaddr_t)S_CUR_EQ_FREE*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=(uint64_t)var_cur, .src=(uint64_t)var_free });

  bitaddr_t readnf_src = vm_proc_slot_field_ip(vm, S_READNF, vm->off_src);
  vm_write_inst(vm, img_do + (bitaddr_t)S_PATCH_READNF*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=(uint64_t)readnf_src, .src=(uint64_t)var_cur });

  vm_write_inst(vm, img_do + (bitaddr_t)S_READNF*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=(uint64_t)var_nextfree, .src=0 });

  vm_write_inst(vm, img_do + (bitaddr_t)S_FREE_EQ_NF*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=(uint64_t)var_free, .src=(uint64_t)var_nextfree });

  bitaddr_t prevwrite_dst = vm_proc_slot_field_ip(vm, S_PREV_WRITE, vm->off_dst);
  vm_write_inst(vm, img_do + (bitaddr_t)S_PATCH_PREV_DST*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=(uint64_t)prevwrite_dst, .src=(uint64_t)var_prev_next_field });

  vm_write_inst(vm, img_do + (bitaddr_t)S_PREV_WRITE*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=0, .src=(uint64_t)var_cur });

  bitaddr_t store_dst = vm_proc_slot_field_ip(vm, S_STORE_CODE, vm->off_dst);
  vm_write_inst(vm, img_do + (bitaddr_t)S_PATCH_STORE_DST*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=(uint64_t)store_dst, .src=(uint64_t)var_cur });

  vm_write_inst(vm, img_do + (bitaddr_t)S_STORE_CODE*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=0, .src=(uint64_t)var_token });

  vm_write_inst(vm, img_do + (bitaddr_t)S_PREVNF_SET*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=(uint64_t)var_prev_next_field, .src=(uint64_t)var_cur });

  const unsigned K=5;
  unsigned jj = A - 1u - K;
  bitaddr_t prevnf_bit5 = var_prev_next_field + (bitaddr_t)jj;
  vm_write_inst(vm, img_do + (bitaddr_t)S_PREVNF_BIT5*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)prevnf_bit5, .src=(uint64_t)(const1_base+40) });

  vm_write_inst(vm, img_do + (bitaddr_t)S_INREQ*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)vm->mmio.in_req, .src=(uint64_t)(const1_base+41) });

  bitaddr_t slot0_dst = vm_proc_slot_field_ip(vm, 0, vm->off_dst);
  bitaddr_t load_src  = vm_proc_slot_field_ip(vm, load_slot, vm->off_src);
  vm_write_inst(vm, img_do + (bitaddr_t)patch_slot*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=(uint64_t)load_src, .src=(uint64_t)slot0_dst });
  vm_write_inst(vm, img_do + (bitaddr_t)load_slot*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->processor_bits, .dst=0, .src=0 });
}



void write_page_end(vm_t *vm, bitaddr_t img_end, bitaddr_t halt_cell,
                           bitaddr_t var_prev_next_field, bitaddr_t const1_base)
{
  nop_fill_image(vm, img_end);
  bitaddr_t A = vm->addr_bits;
  const unsigned S_PATCH_DST=1, S_WRITE=2, S_SETHALT=3;
  bitaddr_t write_dst = vm_proc_slot_field_ip(vm, S_WRITE, vm->off_dst);
  vm_write_inst(vm, img_end + (bitaddr_t)S_PATCH_DST*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=(uint64_t)write_dst, .src=(uint64_t)var_prev_next_field });
  vm_write_inst(vm, img_end + (bitaddr_t)S_WRITE*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=A, .dst=0, .src=(uint64_t)halt_cell });
  vm_write_inst(vm, img_end + (bitaddr_t)S_SETHALT*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=1, .dst=(uint64_t)vm->mmio.halt, .src=(uint64_t)(const1_base+50) });
}


