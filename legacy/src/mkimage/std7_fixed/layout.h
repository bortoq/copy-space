/* file: src/mkimage/std7_fixed/layout.h
 * date: 2026-05-04
 * purpose: compute fixed layout (WORDS_BASE, TESTSCR, pool overlap checks)
 */
#ifndef STD7_FIXED_LAYOUT_H_
#define STD7_FIXED_LAYOUT_H_

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include "space.h"   /* for vm_t, bitaddr_t */

typedef struct {
  bitaddr_t step_bits;

  /* words region */
  unsigned words_region_pages;
  bitaddr_t words_region_bits;
  bitaddr_t words_base;          /* WORDS_BASE */

  /* standardized test scratch */
  size_t    testscr_size_bytes;
  bitaddr_t testscr_size_bits;
  bitaddr_t testscr_base;

  /* pool */
  bitaddr_t pool_base;
  unsigned  pool_cells;
  bitaddr_t pool_end;
} std7_layout_t;

/* returns 0 ok, nonzero on error (prints message to err) */
int std7_fixed_compute_layout(const vm_t *vm,
                              bitaddr_t step_bits,
                              unsigned bsel,
                              bitaddr_t pool_base,
                              unsigned pool_cells,
                              std7_layout_t *out,
                              FILE *err);

#endif