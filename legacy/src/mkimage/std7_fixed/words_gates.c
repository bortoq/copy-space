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


/* ------------------------------------------------------------------ */
/*  32-bit gate words (multi-page, bit-serial via processor slots)     */
/* ------------------------------------------------------------------ */


void write_word_bnot32(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                        bitaddr_t OPA, bitaddr_t OPR,
                        bitaddr_t CONST1, bitaddr_t CONST0)
{
  unsigned last_slot = vm->processor_n - 1u;
  unsigned ips = 3u;
  unsigned bpp = last_slot / ips;
  unsigned rem = 32u;
  unsigned boff = 0u;
  bitaddr_t page = img;

  // compute STEP same as legacy.c
  unsigned bsel = 0;
  while (((bitaddr_t)1u << bsel) < vm->processor_bits) bsel++;
  bitaddr_t STEP = (bitaddr_t)1u << bsel;

  while (rem > 0u) {
    unsigned batch = (rem > bpp) ? bpp : rem;

    nop_fill_image(vm, page);

    for (unsigned i = 0u; i < batch; i++) {
      unsigned s = i * ips;
      bitaddr_t BA = OPA + boff + i;
      bitaddr_t BR = OPR + boff + i;

      /* BR = 1 */
      vm_write_inst(vm, page + (bitaddr_t)(s+0u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=1, .dst=(uint64_t)BR, .src=(uint64_t)(CONST1+0u) });

      /* patch n_lsb of conditional slot with BA */
      bitaddr_t cond_n_lsb = n_lsb_of_slot(vm, s+2u);
      vm_write_inst(vm, page + (bitaddr_t)(s+1u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=1, .dst=(uint64_t)cond_n_lsb, .src=(uint64_t)BA });

      /* if BA then BR = 0 */
      vm_write_inst(vm, page + (bitaddr_t)(s+2u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=0, .dst=(uint64_t)BR, .src=(uint64_t)(CONST0+0u) });
    }

    boff += batch;
    rem  -= batch;

    bitaddr_t nxt = (rem > 0u) ? (page + STEP) : next_img;
    write_chain_load(vm, page, nxt);
    page += STEP;
  }
}


void write_word_band32(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                        bitaddr_t OPA, bitaddr_t OPB, bitaddr_t OPR,
                        bitaddr_t CONST0)
{
  unsigned last_slot = vm->processor_n - 1u;
  unsigned ips = 3u;
  unsigned bpp = last_slot / ips;
  unsigned rem = 32u;
  unsigned boff = 0u;
  bitaddr_t page = img;

  // compute STEP same as legacy.c
  unsigned bsel = 0;
  while (((bitaddr_t)1u << bsel) < vm->processor_bits) bsel++;
  bitaddr_t STEP = (bitaddr_t)1u << bsel;

  while (rem > 0u) {
    unsigned batch = (rem > bpp) ? bpp : rem;

    nop_fill_image(vm, page);

    for (unsigned i = 0u; i < batch; i++) {
      unsigned s = i * ips;
      bitaddr_t BA = OPA + boff + i;
      bitaddr_t BB = OPB + boff + i;
      bitaddr_t BR = OPR + boff + i;

      /* BR = 0 */
      vm_write_inst(vm, page + (bitaddr_t)(s+0u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=1, .dst=(uint64_t)BR, .src=(uint64_t)(CONST0+0u) });

      /* patch n_lsb of conditional slot with BA */
      bitaddr_t cond_n_lsb = n_lsb_of_slot(vm, s+2u);
      vm_write_inst(vm, page + (bitaddr_t)(s+1u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=1, .dst=(uint64_t)cond_n_lsb, .src=(uint64_t)BA });

      /* if BA then BR = BB */
      vm_write_inst(vm, page + (bitaddr_t)(s+2u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=0, .dst=(uint64_t)BR, .src=(uint64_t)BB });
    }

    boff += batch;
    rem  -= batch;

    bitaddr_t nxt = (rem > 0u) ? (page + STEP) : next_img;
    write_chain_load(vm, page, nxt);
    page += STEP;
  }
}


void write_word_bor32(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                       bitaddr_t OPA, bitaddr_t OPB, bitaddr_t OPR,
                       bitaddr_t CONST1, bitaddr_t CONST0)
{
  unsigned last_slot = vm->processor_n - 1u;
  unsigned ips = 5u;
  unsigned bpp = last_slot / ips;
  unsigned rem = 32u;
  unsigned boff = 0u;
  bitaddr_t page = img;

  // compute STEP same as legacy.c
  unsigned bsel = 0;
  while (((bitaddr_t)1u << bsel) < vm->processor_bits) bsel++;
  bitaddr_t STEP = (bitaddr_t)1u << bsel;

  while (rem > 0u) {
    unsigned batch = (rem > bpp) ? bpp : rem;

    nop_fill_image(vm, page);

    for (unsigned i = 0u; i < batch; i++) {
      unsigned s = i * ips;
      bitaddr_t BA = OPA + boff + i;
      bitaddr_t BB = OPB + boff + i;
      bitaddr_t BR = OPR + boff + i;

      /* BR = 0 */
      vm_write_inst(vm, page + (bitaddr_t)(s+0u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=1, .dst=(uint64_t)BR, .src=(uint64_t)(CONST0+0u) });

      /* if BA then BR = 1 */
      bitaddr_t n_lsb_A = n_lsb_of_slot(vm, s+2u);
      vm_write_inst(vm, page + (bitaddr_t)(s+1u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=1, .dst=(uint64_t)n_lsb_A, .src=(uint64_t)BA });
      vm_write_inst(vm, page + (bitaddr_t)(s+2u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=0, .dst=(uint64_t)BR, .src=(uint64_t)(CONST1+0u) });

      /* if BB then BR = 1 */
      bitaddr_t n_lsb_B = n_lsb_of_slot(vm, s+4u);
      vm_write_inst(vm, page + (bitaddr_t)(s+3u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=1, .dst=(uint64_t)n_lsb_B, .src=(uint64_t)BB });
      vm_write_inst(vm, page + (bitaddr_t)(s+4u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=0, .dst=(uint64_t)BR, .src=(uint64_t)(CONST1+0u) });
    }

    boff += batch;
    rem  -= batch;

    bitaddr_t nxt = (rem > 0u) ? (page + STEP) : next_img;
    write_chain_load(vm, page, nxt);
    page += STEP;
  }
}


void write_word_bxor32(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                        bitaddr_t OPA, bitaddr_t OPB, bitaddr_t OPR,
                        bitaddr_t X0, bitaddr_t X1,
                        bitaddr_t CONST1, bitaddr_t CONST0)
{
  unsigned last_slot = vm->processor_n - 1u;
  unsigned ips = 11u;
  unsigned bpp = last_slot / ips;
  unsigned rem = 32u;
  unsigned boff = 0u;
  bitaddr_t page = img;

  // compute STEP same as legacy.c
  unsigned bsel = 0;
  while (((bitaddr_t)1u << bsel) < vm->processor_bits) bsel++;
  bitaddr_t STEP = (bitaddr_t)1u << bsel;

  while (rem > 0u) {
    unsigned batch = (rem > bpp) ? bpp : rem;

    nop_fill_image(vm, page);

    for (unsigned i = 0u; i < batch; i++) {
      unsigned s = i * ips;
      bitaddr_t BA = OPA + boff + i;
      bitaddr_t BB = OPB + boff + i;
      bitaddr_t BR = OPR + boff + i;

      /* X0 = NOT BB (3 instr) */
      vm_write_inst(vm, page + (bitaddr_t)(s+0u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=1, .dst=(uint64_t)X0, .src=(uint64_t)(CONST1+0u) });
      bitaddr_t nl0 = n_lsb_of_slot(vm, s+2u);
      vm_write_inst(vm, page + (bitaddr_t)(s+1u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=1, .dst=(uint64_t)nl0, .src=(uint64_t)BB });
      vm_write_inst(vm, page + (bitaddr_t)(s+2u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=0, .dst=(uint64_t)X0, .src=(uint64_t)(CONST0+0u) });

      /* X1 = NOT BA (3 instr) */
      vm_write_inst(vm, page + (bitaddr_t)(s+3u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=1, .dst=(uint64_t)X1, .src=(uint64_t)(CONST1+0u) });
      bitaddr_t nl1 = n_lsb_of_slot(vm, s+5u);
      vm_write_inst(vm, page + (bitaddr_t)(s+4u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=1, .dst=(uint64_t)nl1, .src=(uint64_t)BA });
      vm_write_inst(vm, page + (bitaddr_t)(s+5u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=0, .dst=(uint64_t)X1, .src=(uint64_t)(CONST0+0u) });

      /* BR = 0 (1 instr) */
      vm_write_inst(vm, page + (bitaddr_t)(s+6u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=1, .dst=(uint64_t)BR, .src=(uint64_t)(CONST0+0u) });

      /* if X1 (BA==0) then BR = BB (2 instr) */
      bitaddr_t nl2 = n_lsb_of_slot(vm, s+8u);
      vm_write_inst(vm, page + (bitaddr_t)(s+7u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=1, .dst=(uint64_t)nl2, .src=(uint64_t)X1 });
      vm_write_inst(vm, page + (bitaddr_t)(s+8u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=0, .dst=(uint64_t)BR, .src=(uint64_t)BB });

      /* if BA then BR = X0 (2 instr) */
      bitaddr_t nl3 = n_lsb_of_slot(vm, s+10u);
      vm_write_inst(vm, page + (bitaddr_t)(s+9u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=1, .dst=(uint64_t)nl3, .src=(uint64_t)BA });
      vm_write_inst(vm, page + (bitaddr_t)(s+10u)*(bitaddr_t)vm->instr_bits,
                    (vm_inst_t){ .n=0, .dst=(uint64_t)BR, .src=(uint64_t)X0 });
    }

    boff += batch;
    rem  -= batch;

    bitaddr_t nxt = (rem > 0u) ? (page + STEP) : next_img;
    write_chain_load(vm, page, nxt);
    page += STEP;
  }
}


