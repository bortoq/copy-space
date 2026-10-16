/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _ASM_COPYSPACE_MMU_H
#define _ASM_COPYSPACE_MMU_H

/* NOMMU still tracks the brk limit (and optional FDPIC load maps). */
#ifdef CONFIG_MMU
#error "copyspace MMU contexts are not implemented"
#endif
#include <asm-generic/mmu.h>

#endif /* _ASM_COPYSPACE_MMU_H */
