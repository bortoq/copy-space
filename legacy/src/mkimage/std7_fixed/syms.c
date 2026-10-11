/* file: src/mkimage/std7_fixed/syms.c
 * date: 2026-05-30
 * purpose: std7_fixed symbol table (symbol → ART address)
 */
#include "syms.h"
#include "words.h"
#include "artifacts.h"
#include <string.h>

/* ------------------------------------------------------------------ */
/*  All non-reserved ART entries (69 symbols).                         */
/*  Excludes reserved indices (3, 8-19) and ART_SYM_TABLE_BASE/END.   */
/* ------------------------------------------------------------------ */
const sym_table_entry_t g_syms[] = {
  /*  0..2 */
  {"HEAD_CELL",   ART_HEAD_CELL},
  {"NEXT_IMG",    ART_NEXT_IMG},
  {"VAR_IP",      ART_VAR_IP},
  /*  4..7 */
  {"WORD_SETUP",  ART_WORD_SETUP},
  {"WORD_INREQ",  ART_WORD_INREQ},
  {"WORD_OUTREQ", ART_WORD_OUTREQ},
  {"WORD_HALT",   ART_WORD_HALT},
  /* 20..24 */
  {"VAR_LOOP",     ART_VAR_LOOP},
  {"WORD_SAVEIP",  ART_WORD_SAVEIP},
  {"WORD_JMP",     ART_WORD_JMP},
  {"WORD_SETOLEN", ART_WORD_SETOLEN},
  {"WORD_IFGOT0",  ART_WORD_IFGOT0},
  /* 25..32 */
  {"VAR_N",    ART_VAR_N},
  {"VAR_DST",  ART_VAR_DST},
  {"VAR_SRC",  ART_VAR_SRC},
  {"WORD_LITN",  ART_WORD_LITN},
  {"WORD_LITD",  ART_WORD_LITD},
  {"WORD_LITS",  ART_WORD_LITS},
  {"WORD_COPY",  ART_WORD_COPY},
  {"WORD_LITIP", ART_WORD_LITIP},
  /* 33..38 */
  {"BA", ART_BA},
  {"BB", ART_BB},
  {"BC", ART_BC},
  {"BR", ART_BR},
  {"T0", ART_T0},
  {"T1", ART_T1},
  /* 39..40 */
  {"WORD_BNOT", ART_WORD_BNOT},
  {"WORD_BAND", ART_WORD_BAND},
  /* 41..45 */
  {"CONST1",   ART_CONST1},
  {"CONST0",   ART_CONST0},
  {"TESTG",    ART_TESTG},
  {"WORD_BOR", ART_WORD_BOR},
  {"WORD_BXOR", ART_WORD_BXOR},
  /* 46..54 */
  {"WORD_ADD24", ART_WORD_ADD24},
  {"VAR_A24",    ART_VAR_A24},
  {"VAR_B24",    ART_VAR_B24},
  {"VAR_SUM24",  ART_VAR_SUM24},
  {"VAR_COUT",   ART_VAR_COUT},
  {"WORD_EQ24",  ART_WORD_EQ24},
  {"VAR_EQ",     ART_VAR_EQ},
  {"WORD_LT24",  ART_WORD_LT24},
  {"VAR_LT",     ART_VAR_LT},
  /* 55..62 */
  {"WORD_LITAP", ART_WORD_LITAP},
  {"WORD_LITBP", ART_WORD_LITBP},
  {"WORD_LITRP", ART_WORD_LITRP},
  {"VAR_AP",     ART_VAR_AP},
  {"VAR_BP",     ART_VAR_BP},
  {"VAR_RP",     ART_VAR_RP},
  {"OFFTAB",     ART_OFFTAB},
  {"WORD_EQ24P", ART_WORD_EQ24P},
  /* 63..64 */
  {"TESTSCR_BASE", ART_TESTSCR_BASE},
  {"TESTSCR_END",  ART_TESTSCR_END},
  /* 65..66 */
  {"BUS_BASE",   ART_BUS_BASE},
  {"TERM0_DESC", ART_TERM0_DESC},
  /* 67..69 */
  {"WORD_LOAD24AP",  ART_WORD_LOAD24AP},
  {"WORD_LOAD24BP",  ART_WORD_LOAD24BP},
  {"WORD_STORE24RP", ART_WORD_STORE24RP},
  /* 70..71 */
  {"WORD_VALIDATE_SCHED", ART_WORD_VALIDATE_SCHED},
  {"WORD_SCHED_INFO",     ART_WORD_SCHED_INFO},
  /* 72 */
  {"WORD_COMPILE_ONE", ART_WORD_COMPILE_ONE},
  /* 73..77 */
  {"VAR_FREE",            ART_VAR_FREE},
  {"VAR_CUR",             ART_VAR_CUR},
  {"VAR_NEXTFREE",        ART_VAR_NEXTFREE},
  {"VAR_PREV_NEXT_FLD",   ART_VAR_PREV_NEXT_FLD},
  {"VAR_TOKEN",           ART_VAR_TOKEN},
  /* 78 */
  {"POOL_BASE", ART_POOL_BASE},
  /* 79..80 */
  {"VAR_SRC_ADDR", ART_VAR_SRC_ADDR},
  {"VAR_SRC_END",  ART_VAR_SRC_END},
  /* 81 */
  {"WORD_SETUP_INSPACE", ART_WORD_SETUP_INSPACE},
  /* 84..92: 32-bit gate words + scratch */
  {"WORD_BNOT32", ART_WORD_BNOT32},
  {"WORD_BAND32", ART_WORD_BAND32},
  {"WORD_BOR32",  ART_WORD_BOR32},
  {"WORD_BXOR32", ART_WORD_BXOR32},
  {"SCR_OPA",     ART_SCR_OPA},
  {"SCR_OPB",     ART_SCR_OPB},
  {"SCR_OPR",     ART_SCR_OPR},
  {"SCR_X0",      ART_SCR_X0},
  {"SCR_X1",      ART_SCR_X1},
  /* 94 */
  {"WORD_C3_RUN", ART_WORD_C3_RUN},
};

const unsigned g_syms_count = sizeof(g_syms) / sizeof(g_syms[0]);

/* ------------------------------------------------------------------ */
/*  Write symbol table to space at sym_base.                           */
/*                                                                     */
/*  Format:                                                             */
/*    sym_count  : 24 bits                                             */
/*    entries[]  :                                                     */
/*      name_len :  8 bits                                             */
/*      name     :  name_len bytes                                     */
/*      art_addr : 24 bits  (workspace_base + art_index * addr_bits)   */
/*                                                                     */
/*  Returns the bit address past the last written byte.                */
/* ------------------------------------------------------------------ */
bitaddr_t std7_fixed_write_symbol_table(
    vm_t *vm,
    bitaddr_t sym_base,
    const sym_table_entry_t *entries,
    unsigned count)
{
  bitaddr_t pos;
  unsigned i;

  /* Guard: reject obviously invalid parameters */
  if (!vm || !vm->space) return sym_base;
  if (!entries || count == 0) {
    /* write empty count and return */
    vm_write_uint(vm, sym_base, 24, 0);
    return sym_base + 24;
  }

  pos = sym_base;

  /* Write sym_count (24 bits) */
  vm_write_uint(vm, pos, 24, (uint64_t)count);
  pos += 24;

  for (i = 0; i < count; i++) {
    const char *name = entries[i].name;
    unsigned name_len;
    bitaddr_t art_addr;
    unsigned j;

    /* Skip NULL name entries gracefully */
    if (!name) name = "";
    name_len = (unsigned)strlen(name);

    /* Write name_len (8 bits) */
    vm_write_uint(vm, pos, 8, (uint64_t)name_len);
    pos += 8;

    /* Write name bytes */
    for (j = 0; j < name_len; j++) {
      vm_write_uint(vm, pos, 8, (uint64_t)(unsigned char)name[j]);
      pos += 8;
    }

    /* art_addr = workspace_base + art_index * addr_bits */
    art_addr = vm->workspace_base
             + (bitaddr_t)entries[i].art_index * (bitaddr_t)vm->addr_bits;

    /* Write art_addr (24 bits) */
    vm_write_uint(vm, pos, 24, (uint64_t)art_addr);
    pos += 24;
  }

  return pos;
}
