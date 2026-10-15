/*
 * EMULATION OF PARALLEL ADDRESS SPACE
 *
 * copyright 2022-12-17, dmitri bortoq, mit license
 * SPDX-License-Identifier: MIT
 */
#include "space.h"

size processor[PROCESSOR_N][INSTRUCTION_FIELDS]; // может быть стоит определить тип "инструкция"? и задать процессор как массив инструкций?
char space[VM_SPACE_BYTES];
const size o[] = {0, N_SIZE, N_SIZE + ADDRESS_SIZE};
const size s[] = {N_SIZE, ADDRESS_SIZE, ADDRESS_SIZE};

static void bit_set_local(unsigned char *p, size_t bitpos, unsigned v)
{
  unsigned char *b = &p[bitpos >> 3];
  unsigned shift = 7u - (unsigned)(bitpos & 7u);
  unsigned char mask = (unsigned char)(1u << shift);
  if(v) *b |= mask;
  else  *b &= (unsigned char)~mask;
}

static void write_field_bits(size_t dst_bit, size value, size width)
{
  size i;
  for(i = 0; i < width; ++i)
    bit_set_local((unsigned char*)space, dst_bit + i, (unsigned)((value >> i) & 1u));
}

int space_init(const void *image, size_t bytes)
{
  if(bytes > sizeof space || (bytes && !image))
    return -1;
  if(bytes)
    memmove(space, image, bytes);
  memset(space + bytes, 0, sizeof space - bytes);
  return 0;
}

/* return bit string of instruction argument as a number */
static inline uint32_t reverse_bits_in_bytes(uint32_t value)
{
  value = ((value & UINT32_C(0x55555555)) << 1) | ((value >> 1) & UINT32_C(0x55555555));
  value = ((value & UINT32_C(0x33333333)) << 2) | ((value >> 2) & UINT32_C(0x33333333));
  return ((value & UINT32_C(0x0f0f0f0f)) << 4) | ((value >> 4) & UINT32_C(0x0f0f0f0f));
}

static inline size get_argument(size src, size n)
{
  size_t byte = src >> 3;
  unsigned offset = src & 7u;
  const unsigned char *p = (const unsigned char *)space + byte;
  if(byte + 4 > sizeof space)
  {
    size value = 0, i;
    for(i = 0; i < n; ++i)
      value |= (size)(((unsigned char)space[(src+i) >> 3] >> (7u-((src+i)&7u))) & 1u) << i;
    return value;
  }
  uint32_t packed = (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
                    ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
  uint32_t value = reverse_bits_in_bytes(packed) >> offset;
  if(n + offset > 32)
    value |= reverse_bits_in_bytes(p[4]) << (32-offset);
  return value & ((UINT32_C(1) << n)-1);
}

/* read "i-th instruction" bit string from bit space to the processor mechanism */
static inline void fetch_instruction(size i)
{
  size a;
  for(a = 0; a < sizeof s / sizeof s[0]; ++a)
    processor[i][a] = get_argument(PROCESSOR_START + i * INSTRUCTION_SIZE + o[a], s[a]);
}

void space_read_processor(void)
{
  size i;
  for(i = 0; i < PROCESSOR_N; ++i)
    fetch_instruction(i);
}

/* load and run copy instructions over bit space */
static int computation(space_observer observe, void *context)
{
  size i;
  for(i = 0; i < PROCESSOR_N; ++i)
  {
    if(i == 1 || i == 2)
      continue;
    fetch_instruction(i);
    if(processor[i][0] == 0)
      continue;
    if(observe)
    {
      space_event event = {0, i, processor[i][0], processor[i][1], processor[i][2], 0, 0};
      observe(&event, context);
    }
    if(processor[i][1] >= SPACE_SIZE || processor[i][2] >= SPACE_SIZE ||
       processor[i][0] > SPACE_SIZE - processor[i][1] ||
       processor[i][0] > SPACE_SIZE - processor[i][2])
      return -1;
    bitcpy(processor[i][0], space, processor[i][2], space, processor[i][1]);
  }
  return 0;
}

/* Store packed copy status; incomplete operations are handled inside space. */
static void channel(FILE *f, size slot, int output, space_observer observe, void *context)
{
  size n = processor[slot][0];
  size a = processor[slot][1];
  size_t copied = 0;
  int code = 0;
  if(n == 0)
    return;
  if((n % CHAR_BIT) != 0 || (a % CHAR_BIT) != 0 ||
     n >= SPACE_SIZE / 2 || a >= SPACE_SIZE || n > SPACE_SIZE - a)
    code = 2;
  else
  {
    clearerr(f);
    copied = output ? fwrite(&space[a / CHAR_BIT], 1, n / CHAR_BIT, f)
                    : fread(&space[a / CHAR_BIT], 1, n / CHAR_BIT, f);
    if(copied != n / CHAR_BIT)
      code = (ferror(f) || output) ? 2 : 1;
  }
  write_field_bits(PROCESSOR_START + slot * INSTRUCTION_SIZE + o[2],
                   (size)(copied * CHAR_BIT * 2) | (code == 2), s[2]);
  if(observe)
  {
    space_event event = {1, slot, n, a, processor[slot][2],
                         (size)(copied * CHAR_BIT), code == 2};
    observe(&event, context);
  }
}

/* Service the current OUT and IN channel instructions. */
static void channels(FILE *in, FILE *out, space_observer observe, void *context)
{
  fetch_instruction(2);
  fetch_instruction(1);
  channel(out, 2, 1, observe, context);
  channel(in, 1, 0, observe, context);
}

int space_active(void)
{
  size i;
  space_read_processor();
  for(i = 0; i < PROCESSOR_N; ++i)
    if(processor[i][0] != 0)
      return 1;
  return 0;
}

space_step_result space_step(FILE *in, FILE *out, space_observer observe, void *context)
{
  if(!space_active())
    return SPACE_STEP_IDLE;
  channels(in, out, observe, context);
  return computation(observe, context) == 0 ? SPACE_STEP_DONE : SPACE_STEP_ERROR;
}
