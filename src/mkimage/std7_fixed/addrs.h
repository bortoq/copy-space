/* file: src/mkimage/std7_fixed/addrs.h
 * date: 2026-05-04
 * purpose: address bundle for std7_fixed artifacts table (ART)
 */
#ifndef STD7_FIXED_ADDRS_H_
#define STD7_FIXED_ADDRS_H_

#include "space.h"   /* bitaddr_t */

typedef struct std7_addrs_t {
  /* 0..2 */
  bitaddr_t head_cell;     /* ART[0] */
  bitaddr_t next_img;      /* ART[1] */
  bitaddr_t var_ip;        /* ART[2] */

  /* 4..7 */
  bitaddr_t word_setup;    /* ART[4] */
  bitaddr_t word_inreq;    /* ART[5] */
  bitaddr_t word_outreq;   /* ART[6] */
  bitaddr_t word_halt;     /* ART[7] */

  /* 20..24 */
  bitaddr_t var_loop;      /* ART[20] */
  bitaddr_t word_saveip;   /* ART[21] */
  bitaddr_t word_jmp;      /* ART[22] */
  bitaddr_t word_setolen;  /* ART[23] */
  bitaddr_t word_ifgot0;   /* ART[24] */

  /* 25..32 */
  bitaddr_t var_n;         /* ART[25] */
  bitaddr_t var_dst;       /* ART[26] */
  bitaddr_t var_src;       /* ART[27] */
  bitaddr_t word_litn;     /* ART[28] */
  bitaddr_t word_litd;     /* ART[29] */
  bitaddr_t word_lits;     /* ART[30] */
  bitaddr_t word_copy;     /* ART[31] */
  bitaddr_t word_litip;    /* ART[32] */

  /* 33..38 */
  bitaddr_t ba;            /* ART[33] */
  bitaddr_t bb;            /* ART[34] */
  bitaddr_t bc;            /* ART[35] */
  bitaddr_t br;            /* ART[36] */
  bitaddr_t t0;            /* ART[37] */
  bitaddr_t t1;            /* ART[38] */

  /* 39..40 */
  bitaddr_t word_bnot;     /* ART[39] */
  bitaddr_t word_band;     /* ART[40] */

  /* 41..45 */
  bitaddr_t const1;        /* ART[41] */
  bitaddr_t const0;        /* ART[42] */
  bitaddr_t testg;         /* ART[43] (policy: == TESTSCR_BASE) */
  bitaddr_t word_bor;      /* ART[44] */
  bitaddr_t word_bxor;     /* ART[45] */

  /* 2a: 46..54 */
  bitaddr_t word_add24;    /* ART[46] */
  bitaddr_t var_a24;       /* ART[47] */
  bitaddr_t var_b24;       /* ART[48] */
  bitaddr_t var_sum24;     /* ART[49] */
  bitaddr_t var_cout;      /* ART[50] */
  bitaddr_t word_eq24;     /* ART[51] */
  bitaddr_t var_eq;        /* ART[52] */
  bitaddr_t word_lt24;     /* ART[53] */
  bitaddr_t var_lt;        /* ART[54] */

  /* 2b: 55..62 */
  bitaddr_t word_litap;    /* ART[55] */
  bitaddr_t word_litbp;    /* ART[56] */
  bitaddr_t word_litrp;    /* ART[57] */
  bitaddr_t var_ap;        /* ART[58] */
  bitaddr_t var_bp;        /* ART[59] */
  bitaddr_t var_rp;        /* ART[60] */
  bitaddr_t offtab;        /* ART[61] */
  bitaddr_t word_eq24p;    /* ART[62] */

  /* scratch: 63..64 */
  bitaddr_t testscr_base;  /* ART[63] */
  bitaddr_t testscr_end;   /* ART[64] == END (1 past end) */

  /* devices/bus: 65..66 */
  bitaddr_t bus_base;      /* ART[65] */
  bitaddr_t term0_desc;    /* ART[66] */
  /* 2b block-pointer primitives (appended ABI): 67..69 */
  bitaddr_t word_load24ap;    /* ART[67] */
  bitaddr_t word_load24bp;    /* ART[68] */
  bitaddr_t word_store24rp;   /* ART[69] */

  /* scheduler words: 70..71 */
  bitaddr_t word_validate_sched;  /* ART[70] */
  bitaddr_t word_sched_info;      /* ART[71] */

  /* compile words: 72 */
  bitaddr_t word_compile_one;     /* ART[72] */

  /* token compiler variables: 73..77 */
  bitaddr_t var_free;             /* ART[73] */
  bitaddr_t var_cur;              /* ART[74] */
  bitaddr_t var_nextfree;         /* ART[75] */
  bitaddr_t var_prev_next_field;  /* ART[76] */
  bitaddr_t var_token;            /* ART[77] */

  /* pool base: 78 */
  bitaddr_t pool_base;            /* ART[78] */

  /* in-space source variables: 79..80 */
  bitaddr_t var_src_addr;         /* ART[79] */
  bitaddr_t var_src_end;          /* ART[80] */

  /* setup inspace word: 81 */
  bitaddr_t word_setup_inspace;   /* ART[81] */

  /* C3_RUN: 94 */
  bitaddr_t word_c3_run;          /* ART[94] */

} std7_addrs_t;

#endif
