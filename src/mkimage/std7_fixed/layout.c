/* file: src/mkimage/std7_fixed/layout.c
 * date: 2026-05-04
 * purpose: compute fixed layout (WORDS_BASE, TESTSCR, pool overlap checks)
 */
#include "layout.h"

/* align DOWN to power-of-two boundary */
static bitaddr_t align_down_pow2(bitaddr_t x, bitaddr_t align_pow2) {
  if (align_pow2 == 0) return x;
  return x & ~(align_pow2 - 1u);
}

int std7_fixed_compute_layout(const vm_t *vm,
                              bitaddr_t step_bits,
                              unsigned bsel,
                              bitaddr_t pool_base,
                              unsigned pool_cells,
                              std7_layout_t *out,
                              FILE *err)
{
  if (!vm || !out) return 1;

  std7_layout_t L;
  L.step_bits = step_bits;

  L.words_region_pages = 128;
  L.words_region_bits = (bitaddr_t)L.words_region_pages * step_bits;

  if (L.words_region_bits + 1024u > vm->space_bits) {
    if (err) fprintf(err, "words region too big\n");
    return 1;
  }

  /* match legacy logic: WORDS_BASE = align_pow2(space_bits - region_bits, 1<<(bsel+1)) */
  bitaddr_t align_bits = (bitaddr_t)1u << (bsel + 1u);
  L.words_base = align_down_pow2(vm->space_bits - L.words_region_bits, align_bits);

  /* standardized test scratch just before WORDS_BASE */
  L.testscr_size_bytes = 8192u;
  L.testscr_size_bits  = (bitaddr_t)L.testscr_size_bytes * 8u;
  L.testscr_base       = (L.words_base >= L.testscr_size_bits) ? (L.words_base - L.testscr_size_bits) : 0;

  /* pool */
  L.pool_base  = pool_base;
  L.pool_cells = pool_cells;
  L.pool_end   = pool_base + (bitaddr_t)pool_cells * 64u;

  /* IMPORTANT: pool must not overlap scratch+words region. Keep some guard. */
  if (L.pool_end + 4096u > L.testscr_base) {
    if (err) {
      fprintf(err,
              "POOL overlaps fixed region: pool_end(byte)=%llu TESTSCR_BASE(byte)=%llu WORDS_BASE(byte)=%llu\n",
              (unsigned long long)(L.pool_end >> 3),
              (unsigned long long)(L.testscr_base >> 3),
              (unsigned long long)(L.words_base >> 3));
    }
    *out = L; /* still return computed numbers for debugging */
    return 1;
  }

  *out = L;
  return 0;
}