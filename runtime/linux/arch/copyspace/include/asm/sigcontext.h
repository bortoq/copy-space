/* SPDX-License-Identifier: GPL-2.0-only WITH Linux-syscall-note */
#ifndef _ASM_COPYSPACE_SIGCONTEXT_H
#define _ASM_COPYSPACE_SIGCONTEXT_H

/*
 * Signal context for copyspace: 32 integer fields plus eight spare words
 * where other ports keep FP state. This target has no FPU or vector unit;
 * the layout is nominal and noted as such until signal delivery code lands.
 * It shadows the RISC-V UAPI sigcontext for copyspace builds only.
 */
#include <asm/ptrace.h>

#ifndef __ASSEMBLY__

struct sigcontext {
	struct user_regs_struct sc_regs;
	unsigned long sc_reserved[8];
};

#endif /* !__ASSEMBLY__ */

#endif /* _ASM_COPYSPACE_SIGCONTEXT_H */
