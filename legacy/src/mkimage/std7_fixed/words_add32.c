#include "words.h"
#include "words_int.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>

void write_word_add32(vm_t *vm, bitaddr_t img, bitaddr_t next_img,
                       bitaddr_t OPA, bitaddr_t OPB, bitaddr_t OPR,
                       bitaddr_t BA, bitaddr_t BB, bitaddr_t BC, bitaddr_t BR,
                       bitaddr_t T0, bitaddr_t T1,
                       bitaddr_t X0, bitaddr_t X1,
                       bitaddr_t CONST1, bitaddr_t CONST0)
{
  unsigned bsel = 0;
  while (((bitaddr_t)1u << bsel) < vm->processor_bits) bsel++;
  bitaddr_t STEP = (bitaddr_t)1u << bsel;

  for (unsigned i = 0; i < 32; i++) {
    unsigned byte_index = 3u - (i / 8u);
    unsigned bit_in_byte = 7u - (i % 8u);

    bitaddr_t Abit = OPA + (bitaddr_t)byte_index * 8u + (bitaddr_t)bit_in_byte;
    bitaddr_t Bbit = OPB + (bitaddr_t)byte_index * 8u + (bitaddr_t)bit_in_byte;
    bitaddr_t Sbit = OPR + (bitaddr_t)byte_index * 8u + (bitaddr_t)bit_in_byte;

    bitaddr_t page = img + (bitaddr_t)i * STEP;
    bitaddr_t nxt  = (i + 1u < 32) ? (page + STEP) : next_img;

    write_word_add24_micro(vm, page, nxt,
                           Abit, Bbit, Sbit,
                           (i == 0), (i == 31),
                           X0,
                           BA, BB, BC, BR, T0, T1, X0, X1,
                           CONST1, CONST0);
  }
}
