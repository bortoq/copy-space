/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_COPYSPACE_IRQFLAGS_H
#define _ASM_COPYSPACE_IRQFLAGS_H

#include <linux/compiler.h>

/*
 * Single-hart interrupt flags for copyspace. The guest has no interrupt
 * enable control: interrupts are never masked here, so the disabled query
 * is constantly false and save/restore round-trip a zero flag with only a
 * compiler barrier. Correct only while the guest stays single-hart; SMP
 * configurations are refused by asm/barrier.h.
 */
static __always_inline unsigned long arch_local_save_flags(void)
{
	return 0UL;
}

static __always_inline void arch_local_irq_enable(void)
{
	barrier();
}

static __always_inline void arch_local_irq_disable(void)
{
	barrier();
}

static __always_inline unsigned long arch_local_irq_save(void)
{
	barrier();
	return 0UL;
}

static __always_inline int arch_irqs_disabled_flags(unsigned long flags)
{
	(void)flags;
	return 0;
}

static __always_inline int arch_irqs_disabled(void)
{
	return 0;
}

static __always_inline void arch_local_irq_restore(unsigned long flags)
{
	(void)flags;
	barrier();
}

#endif /* _ASM_COPYSPACE_IRQFLAGS_H */
