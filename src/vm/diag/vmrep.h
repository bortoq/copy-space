/* file: src/vm/diag/vmrep.h
 * date: 2026-05-04
 * purpose: vmrep (bits-per-tick reporting, latency/throughput window)
 */
#ifndef COPYSPACE_VMREP_H_
#define COPYSPACE_VMREP_H_

#include <stdint.h>
#include <stddef.h>

void vmrep_tick_begin(size_t slots_cap);
void vmrep_note_copy(uint64_t dst, uint64_t n);
void vmrep_tick_end(void);

#endif
