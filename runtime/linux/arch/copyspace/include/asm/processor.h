/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _ASM_COPYSPACE_PROCESSOR_H
#define _ASM_COPYSPACE_PROCESSOR_H

#include <linux/compiler.h>

/*
 * Single-hart processor view for copyspace. The task allocation itself is
 * the stack page (thread_info stays at offset zero of task_struct, as on
 * other architectures). Relaxing in spin loops is a compiler barrier plus
 * a no-op copy; there is no pause instruction on this target.
 */
/* task_stack_page() comes from sched/task_stack.h; thread_info stays at
 * offset zero of task_struct, as on other architectures. */
struct thread_struct {
};

static __always_inline void cpu_relax(void)
{
	barrier();
	__asm__ __volatile__("copy.nop" ::: "memory");
}

#endif /* _ASM_COPYSPACE_PROCESSOR_H */
