/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_COPYSPACE_CMPXCHG_H
#define _ASM_COPYSPACE_CMPXCHG_H

#include <linux/types.h>
#include <linux/compiler.h>
#include <linux/bug.h>

/* Single non-preemptive execution stream only. SMP ordering is rejected by
 * asm/barrier.h; these operations do not implement interrupt exclusion. */
extern unsigned int __sync_lock_test_and_set_4(volatile void *, unsigned int);
extern unsigned long long __sync_lock_test_and_set_8(volatile void *, unsigned long long);
extern unsigned int __sync_val_compare_and_swap_4(volatile void *, unsigned int, unsigned int);
extern unsigned long long __sync_val_compare_and_swap_8(volatile void *, unsigned long long,
						     unsigned long long);

/* Sub-word accesses touch exactly the object, including signed operands.
 * Widening a signed byte before a masked word store would corrupt neighbours. */
#define __COPYSPACE_SUBWORD(bits, type) \
static __always_inline type __copyspace_xchg##bits(volatile type *p, type n) \
{ \
	type old; barrier(); old = *p; *p = n; barrier(); return old; \
} \
static __always_inline type __copyspace_cmpxchg##bits(volatile type *p, type o, type n) \
{ \
	type old; barrier(); old = *p; if (old == o) *p = n; barrier(); return old; \
}
__COPYSPACE_SUBWORD(8, u8)
__COPYSPACE_SUBWORD(16, u16)
#undef __COPYSPACE_SUBWORD

/* Union views preserve scalar/pointer representations without converting
 * 64-bit values through the target's 32-bit unsigned long or void *. */
#define __COPYSPACE_ATOMIC_VALUE(ptr) \
	union { __typeof__(*(ptr)) value; u8 b; u16 h; u32 w; u64 d; }

#define arch_xchg(ptr, x) \
({ \
	__auto_type __cs_xp = (ptr); \
	__COPYSPACE_ATOMIC_VALUE(__cs_xp) __cs_xn = { .value = (x) }, __cs_xr; \
	switch (sizeof(*__cs_xp)) { \
	case 1: __cs_xr.b = __copyspace_xchg8((volatile u8 *)__cs_xp, __cs_xn.b); break; \
	case 2: __cs_xr.h = __copyspace_xchg16((volatile u16 *)__cs_xp, __cs_xn.h); break; \
	case 4: __cs_xr.w = __sync_lock_test_and_set_4(__cs_xp, __cs_xn.w); break; \
	case 8: __cs_xr.d = __sync_lock_test_and_set_8(__cs_xp, __cs_xn.d); break; \
	default: BUILD_BUG(); \
	} \
	__cs_xr.value; \
})
#define arch_xchg_relaxed arch_xchg
#define arch_xchg_acquire arch_xchg
#define arch_xchg_release arch_xchg
#define arch_xchg_local arch_xchg

#define arch_cmpxchg(ptr, o, n) \
({ \
	__auto_type __cs_cp = (ptr); \
	__COPYSPACE_ATOMIC_VALUE(__cs_cp) __cs_co = { .value = (o) }, \
		__cs_cn = { .value = (n) }, __cs_cr; \
	switch (sizeof(*__cs_cp)) { \
	case 1: __cs_cr.b = __copyspace_cmpxchg8((volatile u8 *)__cs_cp, __cs_co.b, __cs_cn.b); break; \
	case 2: __cs_cr.h = __copyspace_cmpxchg16((volatile u16 *)__cs_cp, __cs_co.h, __cs_cn.h); break; \
	case 4: __cs_cr.w = __sync_val_compare_and_swap_4(__cs_cp, __cs_co.w, __cs_cn.w); break; \
	case 8: __cs_cr.d = __sync_val_compare_and_swap_8(__cs_cp, __cs_co.d, __cs_cn.d); break; \
	default: BUILD_BUG(); \
	} \
	__cs_cr.value; \
})
#define arch_cmpxchg_relaxed arch_cmpxchg
#define arch_cmpxchg_acquire arch_cmpxchg
#define arch_cmpxchg_release arch_cmpxchg
#define arch_cmpxchg_local arch_cmpxchg
#define arch_cmpxchg64 arch_cmpxchg
#define arch_cmpxchg64_relaxed arch_cmpxchg
#define arch_cmpxchg64_acquire arch_cmpxchg
#define arch_cmpxchg64_release arch_cmpxchg
#define arch_cmpxchg64_local arch_cmpxchg

#define arch_try_cmpxchg(ptr, oldp, new) \
({ \
	__auto_type __cs_tp = (ptr); \
	__auto_type __cs_top = (oldp); \
	__typeof__(*__cs_tp) __cs_to = *__cs_top; \
	__typeof__(*__cs_tp) __cs_tr = arch_cmpxchg(__cs_tp, __cs_to, (new)); \
	if (__cs_tr != __cs_to) *__cs_top = __cs_tr; \
	(__cs_tr == __cs_to); \
})
#define arch_try_cmpxchg64 arch_try_cmpxchg

#endif /* _ASM_COPYSPACE_CMPXCHG_H */
