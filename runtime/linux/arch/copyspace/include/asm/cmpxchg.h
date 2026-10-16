/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_COPYSPACE_CMPXCHG_H
#define _ASM_COPYSPACE_CMPXCHG_H

#include <linux/types.h>
#include <linux/compiler.h>
#include <linux/bug.h>

/*
 * Single-hart exchange and compare-exchange for copyspace. The guest
 * executes on one hart with sequentially executed copies, so each
 * primitive is a plain volatile access plus a compiler barrier, provided
 * here by the out-of-line __sync_* helpers (plain atomic load/store need
 * no helper). Correct only while the guest stays single-hart with no
 * preemptive interruption inside a primitive; no SMP claim. All ordering
 * variants are identical on this execution model.
 */
extern unsigned int __sync_lock_test_and_set_4(volatile void *, unsigned int);
extern unsigned long long __sync_lock_test_and_set_8(volatile void *, unsigned long long);
extern unsigned int __sync_val_compare_and_swap_4(volatile void *, unsigned int, unsigned int);
extern unsigned long long __sync_val_compare_and_swap_8(volatile void *, unsigned long long,
							unsigned long long);

static __always_inline unsigned long __xchg_u32(volatile u32 *p, u32 n)
{
	return __sync_lock_test_and_set_4((volatile void *)p, (unsigned int)n);
}

static __always_inline unsigned long long __xchg_u64(volatile u64 *p, u64 n)
{
	return __sync_lock_test_and_set_8((volatile void *)p, (unsigned long long)n);
}

/* Sub-word exchange through the containing aligned word. Single attempt
 * suffices on one hart; barrier() orders the compiler around it. */
#define __XCHG_MASKED(type, ptr, x)						\
({										\
	__typeof__(*(ptr)) __x = (x);					\
	volatile u32 *__a = (volatile u32 *)((unsigned long)(ptr) & ~3UL); \
	unsigned int __s = ((unsigned long)(ptr) & 3UL) * 8U;		\
	u32 __mask = (u32)(((1ULL << (sizeof(type) * 8U)) - 1ULL) << __s); \
	u32 __old = *__a;							\
	barrier();								\
	*__a = (__old & ~__mask) | ((u32)__x << __s);			\
	barrier();								\
	(__typeof__(*(ptr)))((__old & __mask) >> __s);			\
})

#define arch_xchg(ptr, x)							\
({										\
	__typeof__(*(ptr)) __ret;						\
	switch (sizeof(*(ptr))) {						\
	case 1: __ret = __XCHG_MASKED(u8, (ptr), (x)); break;			\
	case 2: __ret = __XCHG_MASKED(u16, (ptr), (x)); break;			\
	case 4: __ret = (__typeof__(*(ptr)))__xchg_u32((volatile u32 *)(ptr), (u32)(x)); break; \
	case 8: __ret = (__typeof__(*(ptr)))(void *)(unsigned long)__xchg_u64((volatile u64 *)(ptr), (u64)(unsigned long)(x)); break; \
	default: BUILD_BUG();							\
	}									\
	__ret;									\
})

#define arch_xchg_relaxed	arch_xchg
#define arch_xchg_acquire	arch_xchg
#define arch_xchg_release	arch_xchg
#define arch_xchg_local		arch_xchg

/* Sub-word compare-exchange through the containing aligned word. */
#define __CMPXCHG_MASKED(type, ptr, o, n)					\
({										\
	__typeof__(*(ptr)) __o = (o), __n = (n);				\
	volatile u32 *__a = (volatile u32 *)((unsigned long)(ptr) & ~3UL); \
	unsigned int __s = ((unsigned long)(ptr) & 3UL) * 8U;		\
	u32 __mask = (u32)(((1ULL << (sizeof(type) * 8U)) - 1ULL) << __s); \
	u32 __oldx = (u32)__o << __s, __newx = (u32)__n << __s;		\
	u32 __cur = *__a;							\
	barrier();								\
	if ((__cur & __mask) == (__oldx & __mask))				\
		*__a = (__cur & ~__mask) | (__newx & __mask);		\
	barrier();								\
	(__typeof__(*(ptr)))((__cur & __mask) >> __s);			\
})

#define arch_cmpxchg(ptr, o, n)							\
({										\
	__typeof__(*(ptr)) __ret;						\
	switch (sizeof(*(ptr))) {						\
	case 1: __ret = __CMPXCHG_MASKED(u8, (ptr), (o), (n)); break;		\
	case 2: __ret = __CMPXCHG_MASKED(u16, (ptr), (o), (n)); break;		\
	case 4: __ret = (__typeof__(*(ptr)))__sync_val_compare_and_swap_4( \
		(volatile void *)(ptr), (unsigned int)(u32)(o), (unsigned int)(u32)(n)); break; \
	case 8: __ret = (__typeof__(*(ptr)))__sync_val_compare_and_swap_8( \
		(volatile void *)(ptr), (unsigned long long)(u64)(unsigned long)(o),	\
		(unsigned long long)(u64)(unsigned long)(n)); break;			\
	default: BUILD_BUG();							\
	}									\
	__ret;									\
})

#define arch_cmpxchg_relaxed	arch_cmpxchg
#define arch_cmpxchg_acquire	arch_cmpxchg
#define arch_cmpxchg_release	arch_cmpxchg
#define arch_cmpxchg_local	arch_cmpxchg

#define arch_cmpxchg64		arch_cmpxchg
#define arch_cmpxchg64_relaxed	arch_cmpxchg
#define arch_cmpxchg64_acquire	arch_cmpxchg
#define arch_cmpxchg64_release	arch_cmpxchg
#define arch_cmpxchg64_local	arch_cmpxchg

#define arch_try_cmpxchg(ptr, oldp, new)					\
({										\
	__typeof__(*(ptr)) __o = *(oldp), __r = arch_cmpxchg((ptr), __o, (new)); \
	if (__r != __o)								\
		*(oldp) = __r;							\
	(__r == __o);								\
})

#define arch_try_cmpxchg64	arch_try_cmpxchg

#endif /* _ASM_COPYSPACE_CMPXCHG_H */
