/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_COPYSPACE_CURRENT_H
#define _ASM_COPYSPACE_CURRENT_H

struct task_struct;

/*
 * Single-hart current task: a plain global pointer. No thread-pointer
 * register exists on this target; with one hart and no preemption inside
 * guest primitives a global is sufficient. SMP configurations are refused
 * by asm/barrier.h.
 */
extern struct task_struct *copyspace_current;

#define get_current()	(copyspace_current)
#define current		get_current()

#endif /* _ASM_COPYSPACE_CURRENT_H */
