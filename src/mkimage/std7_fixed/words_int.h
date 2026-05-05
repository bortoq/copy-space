/* file: src/mkimage/std7_fixed/words_int.h
 * date: 2026-05-04
 * purpose: internal helpers shared by std7_fixed word/page builders
 */
#ifndef STD7_FIXED_WORDS_INT_H_
#define STD7_FIXED_WORDS_INT_H_

#include "space.h"

/* image/page utils */
void nop_fill_image(vm_t *vm, bitaddr_t img_base);
void nop_fill_processor(vm_t *vm);
void write_chain_load(vm_t *vm, bitaddr_t img, bitaddr_t next_img);
void write_word_return_to_next(vm_t *vm, bitaddr_t word_img, bitaddr_t next_img);
void write_cell(vm_t *vm, bitaddr_t cell_base, bitaddr_t code_ptr, bitaddr_t next_ptr);

/* bool-op helpers used inside pages */
bitaddr_t n_lsb_of_slot(vm_t *vm, unsigned slot);

void emit_band(vm_t *vm, bitaddr_t img, unsigned *pslot,
               bitaddr_t BA, bitaddr_t BB, bitaddr_t R,
               bitaddr_t CONST0);

void emit_bor(vm_t *vm, bitaddr_t img, unsigned *pslot,
              bitaddr_t BA, bitaddr_t BB, bitaddr_t R,
              bitaddr_t CONST1, bitaddr_t CONST0);

void emit_bnot(vm_t *vm, bitaddr_t img, unsigned *pslot,
               bitaddr_t BA, bitaddr_t R,
               bitaddr_t CONST1, bitaddr_t CONST0);

void emit_bxor(vm_t *vm, bitaddr_t img, unsigned *pslot,
               bitaddr_t BA, bitaddr_t BB, bitaddr_t R,
               bitaddr_t X0, bitaddr_t X1,
               bitaddr_t CONST1, bitaddr_t CONST0);

#endif
