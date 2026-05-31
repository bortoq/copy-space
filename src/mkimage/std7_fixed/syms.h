/* syms.h — Symbol Table for self-hosting compiler */
#ifndef STD7_FIXED_SYMS_H_
#define STD7_FIXED_SYMS_H_

#include "space.h"

typedef struct {
  const char *name;    /* word name (ASCII, UPPERCASE) */
  unsigned art_index;  /* ART index (std7_art_idx_t value) */
} sym_table_entry_t;

/* Write Symbol Table to space. Returns end bitaddr. */
bitaddr_t std7_fixed_write_symbol_table(
    vm_t *vm,
    bitaddr_t sym_base,
    const sym_table_entry_t *entries,
    unsigned count);

#endif /* STD7_FIXED_SYMS_H_ */
