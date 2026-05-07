/* file: src/mkimage/std7_fixed/words_all.h
 * date: 2026-05-04
 * purpose: exported builders for std7_fixed pages/words (extracted from legacy.c)
 */
#ifndef STD7_FIXED_WORDS_ALL_H_
#define STD7_FIXED_WORDS_ALL_H_

#include "space.h"

void write_word_load24ap(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                         bitaddr_t VAR_A24, bitaddr_t VAR_AP);

void write_word_load24bp(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                         bitaddr_t VAR_B24, bitaddr_t VAR_BP);

void write_word_store24rp(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                          bitaddr_t VAR_RP, bitaddr_t VAR_SUM24);
void nop_fill_processor(vm_t *vm);
void write_next_page(vm_t *vm, bitaddr_t next_img,
                            bitaddr_t var_ip, bitaddr_t var_code, bitaddr_t var_next,
                            bitaddr_t const1_base);
void write_word_nop(vm_t *vm, bitaddr_t img, bitaddr_t next_img);
void write_word_setup_echo(vm_t *vm, bitaddr_t img, bitaddr_t next_img, bitaddr_t const1_base);
void write_word_inreq(vm_t *vm, bitaddr_t img, bitaddr_t next_img, bitaddr_t const1_base);
void write_word_outreq(vm_t *vm, bitaddr_t img, bitaddr_t next_img, bitaddr_t const1_base);
void write_word_halt(vm_t *vm, bitaddr_t img, bitaddr_t next_img, bitaddr_t const1_base);
void write_word_saveip(vm_t *vm, bitaddr_t img, bitaddr_t next_img, bitaddr_t var_ip, bitaddr_t var_loop);
void write_word_jmp(vm_t *vm, bitaddr_t img, bitaddr_t next_img, bitaddr_t var_ip, bitaddr_t var_loop);
void write_word_setolen(vm_t *vm, bitaddr_t img, bitaddr_t next_img);
void write_word_ifgot0(vm_t *vm,
                              bitaddr_t img, bitaddr_t next_img,
                              bitaddr_t var_ip,
                              bitaddr_t var_flag, bitaddr_t var_z,
                              bitaddr_t const1_base, bitaddr_t const0_base,
                              unsigned bsel);
void write_word_lit_generic(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                                   bitaddr_t var_ip, bitaddr_t var_x,
                                   bitaddr_t const1_base);
void write_word_litip(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                             bitaddr_t var_ip, bitaddr_t var_src,
                             bitaddr_t const1_base);
void write_word_copy(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                            bitaddr_t var_n, bitaddr_t var_dst, bitaddr_t var_src);
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
void write_page_branch(vm_t *vm, bitaddr_t img_branch, bitaddr_t do_base, unsigned bsel);
void write_page_do(vm_t *vm, bitaddr_t img_do, bitaddr_t img_branch,
                          bitaddr_t var_free, bitaddr_t var_cur, bitaddr_t var_nextfree,
                          bitaddr_t var_prev_next_field, bitaddr_t var_token,
                          bitaddr_t const1_base);
void write_page_end(vm_t *vm, bitaddr_t img_end, bitaddr_t halt_cell,
                           bitaddr_t var_prev_next_field, bitaddr_t const1_base);
void write_word_add24_micro(vm_t *vm,
                                   bitaddr_t img, bitaddr_t chain_next,
                                   bitaddr_t Abit, bitaddr_t Bbit, bitaddr_t Sbit,
                                   int is_first, int is_last,
                                   bitaddr_t OUT_COUT,
                                   bitaddr_t BA, bitaddr_t BB, bitaddr_t BC, bitaddr_t BR,
                                   bitaddr_t T0, bitaddr_t T1,
                                   bitaddr_t X0, bitaddr_t X1,
                                   bitaddr_t CONST1, bitaddr_t CONST0);
void write_word_eq24_micro(vm_t *vm,
                                  bitaddr_t img, bitaddr_t chain_next,
                                  bitaddr_t Abit, bitaddr_t Bbit,
                                  int is_first, int is_last,
                                  bitaddr_t OUT_EQ,
                                  bitaddr_t BA, bitaddr_t BB, bitaddr_t BR,
                                  bitaddr_t ACC_NEQ, bitaddr_t SCR,
                                  bitaddr_t X0, bitaddr_t X1,
                                  bitaddr_t CONST1, bitaddr_t CONST0);
void write_word_lt24_micro(vm_t *vm,
                                  bitaddr_t img, bitaddr_t chain_next,
                                  bitaddr_t Abit, bitaddr_t Bbit,
                                  int is_first, int is_last,
                                  bitaddr_t OUT_LT,
                                  bitaddr_t BA, bitaddr_t BB, bitaddr_t BR,
                                  bitaddr_t ST_EQ, bitaddr_t ST_LT,
                                  bitaddr_t SCR_DIFF,
                                  bitaddr_t X0, bitaddr_t X1,
                                  bitaddr_t CONST1, bitaddr_t CONST0);
void write_word_eq24p_micro(vm_t *vm,
                                   bitaddr_t img, bitaddr_t chain_next,
                                   unsigned off5,
                                   int is_first, int is_last,
                                   bitaddr_t VAR_AP, bitaddr_t VAR_BP,
                                   bitaddr_t OFFTAB,
                                   bitaddr_t BA, bitaddr_t BB, bitaddr_t BR,
                                   bitaddr_t ACC_NEQ, bitaddr_t SCR,
                                   bitaddr_t X0, bitaddr_t X1,
                                   bitaddr_t CONST1, bitaddr_t CONST0,
                                   bitaddr_t OUT_EQ);
void write_cell(vm_t *vm, bitaddr_t cell_base, bitaddr_t code_ptr, bitaddr_t next_ptr);

#endif
