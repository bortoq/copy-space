/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _ASM_COPYSPACE_TLB_H
#define _ASM_COPYSPACE_TLB_H

#ifdef CONFIG_MMU
#error "copyspace TLB management is not implemented"
#endif
#include <asm-generic/tlb.h>

#endif /* _ASM_COPYSPACE_TLB_H */
