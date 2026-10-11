/* rv32.h — resident RV32I executor helpers for Copy-Space */

#ifndef COPYSPACE_RV32_H_
#define COPYSPACE_RV32_H_

#include "space.h"

void rv32_trace_reset(vm_t *vm);
int rv32_guest_step(vm_t *vm);

#endif
