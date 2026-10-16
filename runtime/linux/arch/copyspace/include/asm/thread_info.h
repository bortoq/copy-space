/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _ASM_COPYSPACE_THREAD_INFO_H
#define _ASM_COPYSPACE_THREAD_INFO_H

#include <asm/page.h>
#include <asm/processor.h>
#include <linux/const.h>
#include <linux/sizes.h>

/* Single-hart thread information: flags and preempt count only. No separate
 * stacks, IRQ stacks, shadow call stacks or vector state exist here. */
#ifndef CONFIG_THREAD_SIZE_ORDER
#define CONFIG_THREAD_SIZE_ORDER 1
#endif
#define THREAD_SIZE_ORDER	CONFIG_THREAD_SIZE_ORDER
#define THREAD_SIZE		(PAGE_SIZE << THREAD_SIZE_ORDER)
#define THREAD_SHIFT		(PAGE_SHIFT + THREAD_SIZE_ORDER)

#ifndef __ASSEMBLY__

struct thread_info {
	unsigned long		flags;
	int			preempt_count;
};

#define INIT_THREAD_INFO(tsk)			\
{						\
	.flags		= 0,			\
	.preempt_count	= INIT_PREEMPT_COUNT,	\
}

void arch_release_task_struct(struct task_struct *tsk);
int arch_dup_task_struct(struct task_struct *dst, struct task_struct *src);

#endif /* !__ASSEMBLY__ */

#define TIF_NOTIFY_RESUME	1
#define TIF_SIGPENDING		2
#define TIF_NEED_RESCHED	3
#define TIF_RESTORE_SIGMASK	4
#define TIF_MEMDIE		5
#define TIF_NOTIFY_SIGNAL	9
#define TIF_UPROBE		10
#define TIF_32BIT		11

#define _TIF_NOTIFY_RESUME	(1 << TIF_NOTIFY_RESUME)
#define _TIF_SIGPENDING		(1 << TIF_SIGPENDING)
#define _TIF_NEED_RESCHED	(1 << TIF_NEED_RESCHED)
#define _TIF_NOTIFY_SIGNAL	(1 << TIF_NOTIFY_SIGNAL)
#define _TIF_UPROBE		(1 << TIF_UPROBE)

#endif /* _ASM_COPYSPACE_THREAD_INFO_H */
