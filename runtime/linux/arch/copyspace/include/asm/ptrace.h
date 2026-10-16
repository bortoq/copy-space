/* SPDX-License-Identifier: GPL-2.0-only WITH Linux-syscall-note */
#ifndef _ASM_COPYSPACE_PTRACE_H
#define _ASM_COPYSPACE_PTRACE_H

#include <linux/compiler.h>
#include <linux/types.h>

/*
 * Register views for copyspace. The general registers are kept as a plain
 * array; named aliases, trap frame layout and signal delivery code land
 * with entry support. Both the UAPI sigcontext and in-kernel users share
 * these nominal definitions.
 */
struct user_regs_struct {
	unsigned long regs[32];
};

struct pt_regs {
	unsigned long gpr[32];
};

/*
 * No user mode exists yet; entry code that introduces one revisits this.
 * Fault paths that test user_mode() therefore take the kernel side.
 */
#define user_mode(regs)		(0)

#endif /* _ASM_COPYSPACE_PTRACE_H */
