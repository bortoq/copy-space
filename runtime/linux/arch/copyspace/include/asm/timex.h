/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _ASM_COPYSPACE_TIMEX_H
#define _ASM_COPYSPACE_TIMEX_H

#include <linux/compiler.h>
#include <linux/types.h>

typedef unsigned long cycles_t;

/*
 * No cycle counter exists on this target yet; timer code will replace
 * this stub. It only satisfies timex.h users that need the type and the
 * interface to parse.
 */
static inline cycles_t get_cycles(void) { return 0; }
#define get_cycles get_cycles

#endif /* _ASM_COPYSPACE_TIMEX_H */
