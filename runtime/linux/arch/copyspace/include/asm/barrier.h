/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_COPYSPACE_BARRIER_H
#define _ASM_COPYSPACE_BARRIER_H

#ifdef CONFIG_SMP
#error "copyspace SMP ordering is not implemented"
#endif

/* Direct copy programs complete each memory operation before the next.
 * Compiler barriers suffice for this single execution stream. */
#define nop() asm volatile("copy.nop")
#include <asm-generic/barrier.h>

#endif
