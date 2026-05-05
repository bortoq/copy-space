/* file: src/mkimage/std7_fixed/report.c
 * date: 2026-05-04
 * purpose: unified mkimage summary/meta printing (stderr)
 */
#include "report.h"

void std7_fixed_print_summary(FILE *err,
                              const char *out_path,
                              const std7_layout_t *L,
                              bitaddr_t art_base,
                              const std7_addrs_t *A)
{
  if (!err) err = stderr;

  fprintf(err,
          "Built std7_fixed (+2a +EQ24P) image: %s\n"
          "  pool_cells=%u pool_end(byte)=%llu\n"
          "  WORDS_BASE(byte)=%llu STEP(bytes)=%llu\n"
          "  WORD_EQ24P(byte)=%llu OFFTAB(byte)=%llu\n",
          out_path,
          (unsigned)L->pool_cells,
          (unsigned long long)(L->pool_end >> 3),
          (unsigned long long)(L->words_base >> 3),
          (unsigned long long)(L->step_bits  >> 3),
          (unsigned long long)(A->word_eq24p >> 3),
          (unsigned long long)(A->offtab     >> 3));

  /* machine-readable-ish meta for TDD/tools */
  fprintf(err, "  ART(byte)=%llu\n", (unsigned long long)(art_base >> 3));
  fprintf(err, "  TESTSCR_BASE(byte)=%llu\n", (unsigned long long)(A->testscr_base >> 3));
  fprintf(err, "  TESTSCR_SIZE(byte)=%zu\n", (size_t)L->testscr_size_bytes);
}