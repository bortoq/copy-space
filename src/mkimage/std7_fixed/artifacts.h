/* file: src/mkimage/std7_fixed/artifacts.h
 * date: 2026-05-04
 * purpose: std7_fixed ART indices + writer
 */
#ifndef STD7_FIXED_ARTIFACTS_H_
#define STD7_FIXED_ARTIFACTS_H_

#include "space.h"
#include "addrs.h"

typedef enum {
  ART_HEAD_CELL = 0,
  ART_NEXT_IMG  = 1,
  ART_VAR_IP    = 2,

  /* 3 reserved */

  ART_WORD_SETUP  = 4,
  ART_WORD_INREQ  = 5,
  ART_WORD_OUTREQ = 6,
  ART_WORD_HALT   = 7,

  /* 8..19 reserved */

  ART_VAR_LOOP     = 20,
  ART_WORD_SAVEIP  = 21,
  ART_WORD_JMP     = 22,
  ART_WORD_SETOLEN = 23,
  ART_WORD_IFGOT0  = 24,

  ART_VAR_N   = 25,
  ART_VAR_DST = 26,
  ART_VAR_SRC = 27,

  ART_WORD_LITN  = 28,
  ART_WORD_LITD  = 29,
  ART_WORD_LITS  = 30,
  ART_WORD_COPY  = 31,
  ART_WORD_LITIP = 32,

  ART_BA = 33,
  ART_BB = 34,
  ART_BC = 35,
  ART_BR = 36,
  ART_T0 = 37,
  ART_T1 = 38,

  ART_WORD_BNOT = 39,
  ART_WORD_BAND = 40,

  ART_CONST1 = 41,
  ART_CONST0 = 42,
  ART_TESTG  = 43, /* policy: == TESTSCR_BASE */

  ART_WORD_BOR  = 44,
  ART_WORD_BXOR = 45,

  /* 2a */
  ART_WORD_ADD24 = 46,
  ART_VAR_A24    = 47,
  ART_VAR_B24    = 48,
  ART_VAR_SUM24  = 49,
  ART_VAR_COUT   = 50,
  ART_WORD_EQ24  = 51,
  ART_VAR_EQ     = 52,
  ART_WORD_LT24  = 53,
  ART_VAR_LT     = 54,

  /* 2b */
  ART_WORD_LITAP = 55,
  ART_WORD_LITBP = 56,
  ART_WORD_LITRP = 57,
  ART_VAR_AP     = 58,
  ART_VAR_BP     = 59,
  ART_VAR_RP     = 60,
  ART_OFFTAB     = 61,
  ART_WORD_EQ24P = 62,

  /* standardized test scratch */
  ART_TESTSCR_BASE = 63,
  ART_TESTSCR_END  = 64,

  /* device/bus */
  ART_BUS_BASE   = 65,
  ART_TERM0_DESC = 66,

  /* 2b block-pointer primitives (appended ABI) */
  ART_WORD_LOAD24AP  = 67,
  ART_WORD_LOAD24BP  = 68,
  ART_WORD_STORE24RP = 69,

  ART_COUNT = 70
} std7_art_idx_t;

/* Writes standard artifacts table. Leaves unspecified/reserved indices unchanged. */
void std7_fixed_write_artifacts(vm_t *vm, bitaddr_t art_base, const std7_addrs_t *A);

#endif
