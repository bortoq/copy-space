/* file: src/mkimage/std7_fixed/words_gates.c
 * date: 2026-05-04
 * purpose: bitwise gate words extracted from words_core.c
 */
#include "words.h"
#include "words_int.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>

void write_word_bnot(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                            bitaddr_t BA, bitaddr_t BR,
                            bitaddr_t const1_base, bitaddr_t const0_base)
{
  nop_fill_image(vm, img);
  unsigned s=1;
  emit_bnot(vm, img, &s, BA, BR, const1_base, const0_base);
  write_word_return_to_next(vm, img, next_img);
}


void write_word_band(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                            bitaddr_t BA, bitaddr_t BB, bitaddr_t BR,
                            bitaddr_t const0_base)
{
  nop_fill_image(vm, img);
  unsigned s=1;
  emit_band(vm, img, &s, BA, BB, BR, const0_base);
  write_word_return_to_next(vm, img, next_img);
}


void write_word_bor(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                           bitaddr_t BA, bitaddr_t BB, bitaddr_t BR,
                           bitaddr_t const1_base, bitaddr_t const0_base)
{
  nop_fill_image(vm, img);
  unsigned s=1;
  emit_bor(vm, img, &s, BA, BB, BR, const1_base, const0_base);
  write_word_return_to_next(vm, img, next_img);
}


void write_word_bxor(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                            bitaddr_t BA, bitaddr_t BB, bitaddr_t BR,
                            bitaddr_t X0, bitaddr_t X1,
                            bitaddr_t const1_base, bitaddr_t const0_base)
{
  nop_fill_image(vm, img);
  unsigned s=1;
  emit_bxor(vm, img, &s, BA, BB, BR, X0, X1, const1_base, const0_base);
  write_word_return_to_next(vm, img, next_img);
}


