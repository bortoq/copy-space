/* file: src/mkimage/std7_fixed/artifacts.c
 * date: 2026-05-04
 * purpose: write std7_fixed artifacts table (ART)
 */
#include "artifacts.h"

static inline void artw(vm_t *vm, bitaddr_t ART, unsigned idx, bitaddr_t v) {
  vm_write_uint(vm, ART + (bitaddr_t)idx * (bitaddr_t)vm->addr_bits, vm->addr_bits, (uint64_t)v);
}

void std7_fixed_write_artifacts(vm_t *vm, bitaddr_t ART, const std7_addrs_t *A) {
  /* 0..2 */
  artw(vm, ART, ART_HEAD_CELL, A->head_cell);
  artw(vm, ART, ART_NEXT_IMG,  A->next_img);
  artw(vm, ART, ART_VAR_IP,    A->var_ip);

  /* 4..7 */
  artw(vm, ART, ART_WORD_SETUP,  A->word_setup);
  artw(vm, ART, ART_WORD_INREQ,  A->word_inreq);
  artw(vm, ART, ART_WORD_OUTREQ, A->word_outreq);
  artw(vm, ART, ART_WORD_HALT,   A->word_halt);

  /* 20..24 */
  artw(vm, ART, ART_VAR_LOOP,     A->var_loop);
  artw(vm, ART, ART_WORD_SAVEIP,  A->word_saveip);
  artw(vm, ART, ART_WORD_JMP,     A->word_jmp);
  artw(vm, ART, ART_WORD_SETOLEN, A->word_setolen);
  artw(vm, ART, ART_WORD_IFGOT0,  A->word_ifgot0);

  /* 25..32 */
  artw(vm, ART, ART_VAR_N,     A->var_n);
  artw(vm, ART, ART_VAR_DST,   A->var_dst);
  artw(vm, ART, ART_VAR_SRC,   A->var_src);
  artw(vm, ART, ART_WORD_LITN, A->word_litn);
  artw(vm, ART, ART_WORD_LITD, A->word_litd);
  artw(vm, ART, ART_WORD_LITS, A->word_lits);
  artw(vm, ART, ART_WORD_COPY, A->word_copy);
  artw(vm, ART, ART_WORD_LITIP, A->word_litip);

  /* 33..38 */
  artw(vm, ART, ART_BA, A->ba);
  artw(vm, ART, ART_BB, A->bb);
  artw(vm, ART, ART_BC, A->bc);
  artw(vm, ART, ART_BR, A->br);
  artw(vm, ART, ART_T0, A->t0);
  artw(vm, ART, ART_T1, A->t1);

  /* 39..40 */
  artw(vm, ART, ART_WORD_BNOT, A->word_bnot);
  artw(vm, ART, ART_WORD_BAND, A->word_band);

  /* 41..45 */
  artw(vm, ART, ART_CONST1, A->const1);
  artw(vm, ART, ART_CONST0, A->const0);

  /* policy: TESTG is the standardized test scratch base */
  artw(vm, ART, ART_TESTG,  A->testg);

  artw(vm, ART, ART_WORD_BOR,  A->word_bor);
  artw(vm, ART, ART_WORD_BXOR, A->word_bxor);

  /* 2a */
  artw(vm, ART, ART_WORD_ADD24, A->word_add24);
  artw(vm, ART, ART_VAR_A24,    A->var_a24);
  artw(vm, ART, ART_VAR_B24,    A->var_b24);
  artw(vm, ART, ART_VAR_SUM24,  A->var_sum24);
  artw(vm, ART, ART_VAR_COUT,   A->var_cout);
  artw(vm, ART, ART_WORD_EQ24,  A->word_eq24);
  artw(vm, ART, ART_VAR_EQ,     A->var_eq);
  artw(vm, ART, ART_WORD_LT24,  A->word_lt24);
  artw(vm, ART, ART_VAR_LT,     A->var_lt);

  /* 2b */
  artw(vm, ART, ART_WORD_LITAP, A->word_litap);
  artw(vm, ART, ART_WORD_LITBP, A->word_litbp);
  artw(vm, ART, ART_WORD_LITRP, A->word_litrp);
  artw(vm, ART, ART_VAR_AP,     A->var_ap);
  artw(vm, ART, ART_VAR_BP,     A->var_bp);
  artw(vm, ART, ART_VAR_RP,     A->var_rp);
  artw(vm, ART, ART_OFFTAB,     A->offtab);
  artw(vm, ART, ART_WORD_EQ24P, A->word_eq24p);

  /* scratch */
  artw(vm, ART, ART_TESTSCR_BASE, A->testscr_base);
  artw(vm, ART, ART_TESTSCR_END,  A->testscr_end);

  /* device/bus */
  artw(vm, ART, ART_BUS_BASE,   A->bus_base);
  artw(vm, ART, ART_TERM0_DESC, A->term0_desc);

  /* 2b block-pointer primitives */
  artw(vm, ART, ART_WORD_LOAD24AP,  A->word_load24ap);
  artw(vm, ART, ART_WORD_LOAD24BP,  A->word_load24bp);
  artw(vm, ART, ART_WORD_STORE24RP, A->word_store24rp);
}