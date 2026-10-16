/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_COPYSPACE_BITOPS_H
#define _ASM_COPYSPACE_BITOPS_H

#include <linux/compiler.h>

#ifndef _LINUX_BITOPS_H
#error "Only <linux/bitops.h> can be included directly"
#endif

/* C implementations for scans and non-atomic operations. UP atomic bitops
 * below are plain volatile accesses plus a compiler barrier, sufficient on
 * one hart with no preemption inside a primitive; no SMP claim. */
extern unsigned int __sync_fetch_and_or_4(volatile void *, unsigned int);
extern unsigned int __sync_fetch_and_and_4(volatile void *, unsigned int);
extern unsigned int __sync_fetch_and_xor_4(volatile void *, unsigned int);

static __always_inline void set_bit(unsigned int nr, volatile unsigned long *addr)
{
	__sync_fetch_and_or_4((volatile void *)&addr[nr / 32U], 1U << (nr % 32U));
}

static __always_inline void clear_bit(unsigned int nr, volatile unsigned long *addr)
{
	__sync_fetch_and_and_4((volatile void *)&addr[nr / 32U], ~(1U << (nr % 32U)));
}

static __always_inline void change_bit(unsigned int nr, volatile unsigned long *addr)
{
	__sync_fetch_and_xor_4((volatile void *)&addr[nr / 32U], 1U << (nr % 32U));
}

static __always_inline int test_and_set_bit(unsigned int nr, volatile unsigned long *addr)
{
	unsigned int old = __sync_fetch_and_or_4((volatile void *)&addr[nr / 32U],
						 1U << (nr % 32U));
	return (old >> (nr % 32U)) & 1U;
}

static __always_inline int test_and_clear_bit(unsigned int nr, volatile unsigned long *addr)
{
	unsigned int old = __sync_fetch_and_and_4((volatile void *)&addr[nr / 32U],
						  ~(1U << (nr % 32U)));
	return (old >> (nr % 32U)) & 1U;
}

static __always_inline int test_and_change_bit(unsigned int nr, volatile unsigned long *addr)
{
	unsigned int old = __sync_fetch_and_xor_4((volatile void *)&addr[nr / 32U],
						  1U << (nr % 32U));
	return (old >> (nr % 32U)) & 1U;
}
#include <asm-generic/bitops/__ffs.h>
#include <asm-generic/bitops/ffz.h>
#include <asm-generic/bitops/__fls.h>
#include <asm-generic/bitops/ffs.h>
#include <asm-generic/bitops/fls.h>
#include <asm-generic/bitops/fls64.h>
#include <asm-generic/bitops/hweight.h>
#include <asm-generic/bitops/non-atomic.h>

static __always_inline int test_and_set_bit_lock(unsigned int nr, volatile unsigned long *addr)
{
	return test_and_set_bit(nr, addr);
}

static __always_inline void clear_bit_unlock(unsigned int nr, volatile unsigned long *addr)
{
	barrier();
	clear_bit(nr, addr);
}

static __always_inline void set_bit_lock(unsigned int nr, volatile unsigned long *addr)
{
	set_bit(nr, addr);
}

static __always_inline bool arch_xor_unlock_is_negative_byte(unsigned long mask,
							     volatile unsigned long *addr)
{
	unsigned long old = __sync_fetch_and_xor_4((volatile void *)addr, mask);
	barrier();
	return (old & (1UL << 7)) != 0;
}
#define xor_unlock_is_negative_byte arch_xor_unlock_is_negative_byte

#endif /* _ASM_COPYSPACE_BITOPS_H */
