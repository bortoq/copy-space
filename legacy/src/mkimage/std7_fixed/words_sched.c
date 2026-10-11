/* file: src/mkimage/std7_fixed/words_sched.c
 * date: 2026-05-29
 * purpose: scheduler word pages — schedule validation and access in space
 *
 * These words read the schedule data from TESTSCR (as produced by sched_to_f0.py)
 * and provide runtime validation and iteration.
 */
#include "words.h"
#include "words_int.h"
#include <stdint.h>

/*
 * WORD_VALIDATE — read pre-computed valid flag from TESTG+96bits
 * If non-zero, trigger HALT (to indicate validation failure).
 *
 * Slots:
 *   1: read valid_flag from TESTG+96 into bit register BR
 *   2-5: propagate BR into MMIO halt (if BR==1, set halt=1, else nop)
 *    (halt is MSB of mmio.halt which is 1 bit)
 */
void write_word_validate_sched(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                                bitaddr_t testg, bitaddr_t const1_base)
{
  nop_fill_image(vm, img);
  unsigned s = 1;

  /* Valid flag is a single bit at testg + 96 */
  bitaddr_t valid_flag_addr = testg + 96;

  /* Copy 1 bit from valid_flag to halt. If valid_flag is 1, VM halts. */
  vm_write_inst(vm, img + (bitaddr_t)s++ * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = 1,
                             .dst = (uint64_t)vm->mmio.halt,
                             .src = (uint64_t)valid_flag_addr });

  write_word_return_to_next(vm, img, next_img);
}


/*
 * WORD_SCHED_INFO — read schedule header fields into variables
 *
 * After call:
 *   VAR_N   = NUM_TICKS
 *   VAR_DST = NUM_CHUNKS
 *   VAR_SRC = SLOTS
 *
 * Slots:
 *   1: copy NUM_TICKS (24 bits from testg+0) into VAR_N
 *   2: copy NUM_CHUNKS (24 bits from testg+24) into VAR_DST
 *   3: copy SLOTS (24 bits from testg+48) into VAR_SRC
 *   4: copy BW (24 bits from testg+72) into VAR_LOOP
 */
void write_word_sched_info(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                            bitaddr_t testg,
                            bitaddr_t var_n, bitaddr_t var_dst,
                            bitaddr_t var_src)
{
  nop_fill_image(vm, img);
  unsigned s = 1;

  vm_write_inst(vm, img + (bitaddr_t)s++ * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = 24, .dst = (uint64_t)var_n,
                             .src = (uint64_t)(testg + 0) });

  vm_write_inst(vm, img + (bitaddr_t)s++ * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = 24, .dst = (uint64_t)var_dst,
                             .src = (uint64_t)(testg + 24) });

  vm_write_inst(vm, img + (bitaddr_t)s++ * (bitaddr_t)vm->instr_bits,
                (vm_inst_t){ .n = 24, .dst = (uint64_t)var_src,
                             .src = (uint64_t)(testg + 48) });

  write_word_return_to_next(vm, img, next_img);
}
