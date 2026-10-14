/*
 * ADDRESS SPACE DEFINITIONS
 *
 * copyright 2024-10-31, dmitri bortoq, mit license
 * SPDX-License-Identifier: MIT
 */
#ifndef SPACE_H_
#define SPACE_H_

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>

#include "support.h"

/* SPACE CONFIGURATION */
#ifndef VM_SPACE_BYTES
#define VM_SPACE_BYTES ((16u * 1024u * 1024u) / CHAR_BIT)
#endif

#ifndef PROCESSOR_N
#define PROCESSOR_N 256u
#endif

typedef uint32_t size;

/* SPACE SET UP */
enum {
  SPACE_SIZE = (size)VM_SPACE_BYTES * CHAR_BIT,
  INSTRUCTION_FIELDS = 3,
  ADDRESS_SIZE = CEIL_LOG2_U32(SPACE_SIZE),
  N_SIZE = ADDRESS_SIZE - 1,
  INSTRUCTION_SIZE = N_SIZE + 2 * ADDRESS_SIZE,
  PROCESSOR_START = 0,
  PROCESSOR_BITS = PROCESSOR_N * INSTRUCTION_SIZE,
};

typedef char space_configuration_valid[
  (PROCESSOR_N >= 4 && ADDRESS_SIZE > 1 && ADDRESS_SIZE <= 31 &&
   PROCESSOR_BITS < SPACE_SIZE) ? 1 : -1];

extern size processor[PROCESSOR_N][INSTRUCTION_FIELDS];
extern char space[VM_SPACE_BYTES];
extern const size o[];
extern const size s[];
typedef enum {
  SPACE_STEP_DONE,
  SPACE_STEP_IDLE,
  SPACE_STEP_ERROR
} space_step_result;

typedef struct {
  int channel;
  size slot;
  size n;
  size dst;
  size src;
  size copied;
  unsigned error;
} space_event;

typedef void (*space_observer)(const space_event *event, void *context);

int space_init(const void *image, size_t bytes);
void space_read_processor(void);
int space_active(void);
space_step_result space_step(FILE *in, FILE *out, space_observer observe, void *context);

void bitcpy(size_t n_bits, const void *src_org, size_t src_bit, void *dst_org, size_t dst_bit);

#endif /* SPACE_H_ */
