#include "space.h"

/* Independent bit-by-bit oracle for every packed instruction field. */
static size reference(size at, size width)
{
  size value = 0, bit;
  for(bit = 0; bit < width; ++bit)
    value |= (size)(((unsigned char)space[(at+bit)/8] >> (7-(at+bit)%8)) & 1u) << bit;
  return value;
}

static int check(void)
{
  size slot, field;
  space_read_processor();
  for(slot = 0; slot < PROCESSOR_N; ++slot)
    for(field = 0; field < INSTRUCTION_FIELDS; ++field)
      if(processor[slot][field] != reference(slot*INSTRUCTION_SIZE+o[field], s[field]))
      {
        fprintf(stderr, "FAIL decode slot=%u field=%u\n", slot, field);
        return 1;
      }
  return 0;
}

int main(void)
{
  uint32_t random = 0x938f4021u;
  unsigned round;
  size slot, field, bit;
  const size bytes = (PROCESSOR_BITS+7)/8;
  /* Every value of each byte, at every field alignment. */
  for(round = 0; round < 256; ++round)
  {
    memset(space, round, bytes);
    if(check()) return 1;
  }
  /* One bit in each field: all significant bit positions and boundaries. */
  for(bit = 0; bit < ADDRESS_SIZE; ++bit)
  {
    memset(space, 0, bytes);
    for(slot = 0; slot < PROCESSOR_N; ++slot)
      for(field = 0; field < INSTRUCTION_FIELDS; ++field)
        if(bit < s[field])
        {
          size at = slot*INSTRUCTION_SIZE+o[field]+bit;
          space[at/8] |= (char)(0x80u >> (at%8));
        }
    if(check()) return 1;
  }
  for(round = 0; round < 1024; ++round)
  {
    size byte;
    for(byte = 0; byte < bytes; ++byte)
    {
      random ^= random << 13;
      random ^= random >> 17;
      random ^= random << 5;
      space[byte] = (char)random;
    }
    if(check()) return 1;
  }
  printf("OK decode: %u-bit addresses, %u field comparisons\n", ADDRESS_SIZE,
         (256u+ADDRESS_SIZE+1024u)*PROCESSOR_N*INSTRUCTION_FIELDS);
  return 0;
}
