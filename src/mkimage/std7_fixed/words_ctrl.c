/* file: src/mkimage/std7_fixed/words_ctrl.c
 * date: 2026-05-04
 * purpose: control/basic words extracted from words_core.c
 */
#include "words.h"
#include "words_int.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>

void write_word_nop(vm_t *vm, bitaddr_t img, bitaddr_t next_img) {
  nop_fill_image(vm, img);
  write_word_return_to_next(vm, img, next_img);
}


void write_word_setup_echo(vm_t *vm, bitaddr_t img, bitaddr_t next_img, bitaddr_t const1_base) {
  nop_fill_image(vm, img);
  unsigned p_buf=21, p_len=8;
  bitaddr_t in_dst_bit  = vm->mmio.in_dst  + (bitaddr_t)(vm->addr_bits-1u-p_buf);
  bitaddr_t in_len_bit  = vm->mmio.in_len  + (bitaddr_t)(vm->n_bits-1u-p_len);
  bitaddr_t out_src_bit = vm->mmio.out_src + (bitaddr_t)(vm->addr_bits-1u-p_buf);
  bitaddr_t out_len_bit = vm->mmio.out_len + (bitaddr_t)(vm->n_bits-1u-p_len);
  vm_write_inst(vm, img + 1u*(bitaddr_t)vm->instr_bits, (vm_inst_t){ .n=1, .dst=(uint64_t)in_dst_bit,  .src=(uint64_t)(const1_base+20) });
  vm_write_inst(vm, img + 2u*(bitaddr_t)vm->instr_bits, (vm_inst_t){ .n=1, .dst=(uint64_t)in_len_bit,  .src=(uint64_t)(const1_base+21) });
  vm_write_inst(vm, img + 3u*(bitaddr_t)vm->instr_bits, (vm_inst_t){ .n=1, .dst=(uint64_t)out_src_bit, .src=(uint64_t)(const1_base+22) });
  vm_write_inst(vm, img + 4u*(bitaddr_t)vm->instr_bits, (vm_inst_t){ .n=1, .dst=(uint64_t)out_len_bit, .src=(uint64_t)(const1_base+23) });
  write_word_return_to_next(vm, img, next_img);
}


void write_word_inreq(vm_t *vm, bitaddr_t img, bitaddr_t next_img, bitaddr_t const1_base) {
  nop_fill_image(vm, img);
  vm_write_inst(vm, img + 1u*(bitaddr_t)vm->instr_bits, (vm_inst_t){ .n=1, .dst=(uint64_t)vm->mmio.in_req,  .src=(uint64_t)(const1_base+30) });
  write_word_return_to_next(vm, img, next_img);
}


void write_word_outreq(vm_t *vm, bitaddr_t img, bitaddr_t next_img, bitaddr_t const1_base) {
  nop_fill_image(vm, img);
  vm_write_inst(vm, img + 1u*(bitaddr_t)vm->instr_bits, (vm_inst_t){ .n=1, .dst=(uint64_t)vm->mmio.out_req, .src=(uint64_t)(const1_base+31) });
  write_word_return_to_next(vm, img, next_img);
}


void write_word_halt(vm_t *vm, bitaddr_t img, bitaddr_t next_img, bitaddr_t const1_base) {
  nop_fill_image(vm, img);
  vm_write_inst(vm, img + 1u*(bitaddr_t)vm->instr_bits, (vm_inst_t){ .n=1, .dst=(uint64_t)vm->mmio.halt,    .src=(uint64_t)(const1_base+32) });
  write_word_return_to_next(vm, img, next_img);
}



void write_word_saveip(vm_t *vm, bitaddr_t img, bitaddr_t next_img, bitaddr_t var_ip, bitaddr_t var_loop) {
  nop_fill_image(vm, img);
  vm_write_inst(vm, img + 1u*(bitaddr_t)vm->instr_bits, (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)var_loop, .src=(uint64_t)var_ip });
  write_word_return_to_next(vm, img, next_img);
}


void write_word_jmp(vm_t *vm, bitaddr_t img, bitaddr_t next_img, bitaddr_t var_ip, bitaddr_t var_loop) {
  nop_fill_image(vm, img);
  vm_write_inst(vm, img + 1u*(bitaddr_t)vm->instr_bits, (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)var_ip, .src=(uint64_t)var_loop });
  write_word_return_to_next(vm, img, next_img);
}



void write_word_setolen(vm_t *vm, bitaddr_t img, bitaddr_t next_img) {
  nop_fill_image(vm, img);
  vm_write_inst(vm, img + 1u*(bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n=vm->addr_bits, .dst=(uint64_t)vm->mmio.out_len, .src=(uint64_t)vm->mmio.in_got });
  write_word_return_to_next(vm, img, next_img);
}



void write_word_ifgot0(vm_t *vm,
                              bitaddr_t img, bitaddr_t next_img,
                              bitaddr_t var_ip,
                              bitaddr_t var_flag, bitaddr_t var_z,
                              bitaddr_t const1_base, bitaddr_t const0_base,
                              unsigned bsel);

/* ---------- LIT/COPY/LITIP ---------- */
void write_word_lit_generic(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                                   bitaddr_t var_ip, bitaddr_t var_x,
                                   bitaddr_t const1_base);
void write_word_litip(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                             bitaddr_t var_ip, bitaddr_t var_src,
                             bitaddr_t const1_base);
void write_word_copy(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                            bitaddr_t var_n, bitaddr_t var_dst, bitaddr_t var_src);

/* ---------- gate pages (std7) ---------- */
void write_word_bnot(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                            bitaddr_t BA, bitaddr_t BR,
                            bitaddr_t const1_base, bitaddr_t const0_base);
void write_word_band(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                            bitaddr_t BA, bitaddr_t BB, bitaddr_t BR,
                            bitaddr_t const0_base);
void write_word_bor(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                           bitaddr_t BA, bitaddr_t BB, bitaddr_t BR,
                           bitaddr_t const1_base, bitaddr_t const0_base);
void write_word_bxor(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                            bitaddr_t BA, bitaddr_t BB, bitaddr_t BR,
                            bitaddr_t X0, bitaddr_t X1,
                            bitaddr_t const1_base, bitaddr_t const0_base);

/* ---------- token compiler pages ---------- */
void write_page_branch(vm_t *vm, bitaddr_t img_branch, bitaddr_t do_base, unsigned bsel);
void write_page_do(vm_t *vm, bitaddr_t img_do, bitaddr_t img_branch,
                          bitaddr_t var_free, bitaddr_t var_cur, bitaddr_t var_nextfree,
                          bitaddr_t var_prev_next_field, bitaddr_t var_token,
                          bitaddr_t const1_base);
void write_page_end(vm_t *vm, bitaddr_t img_end, bitaddr_t halt_cell,
                           bitaddr_t var_prev_next_field, bitaddr_t const1_base);

/* ---------- 2a micro words (already implemented earlier) ---------- */
/* removed (belongs to 2a module): write_word_add24_micro */

