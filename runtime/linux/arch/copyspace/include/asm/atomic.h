/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef _ASM_COPYSPACE_ATOMIC_H
#define _ASM_COPYSPACE_ATOMIC_H

#include <linux/compiler.h>
#include <linux/types.h>
#include <asm/cmpxchg.h>

/*
 * Single-hart atomic counters for copyspace. Read-modify-write operations
 * lower to the out-of-line __sync_* helpers (plain volatile accesses plus
 * a compiler barrier in the single execution stream). Correct only while
 * the guest stays single-hart with no preemptive interruption inside a
 * primitive; no SMP claim. Ordering variants are identical here.
 */
extern unsigned int __sync_fetch_and_add_4(volatile void *, unsigned int);
extern unsigned int __sync_fetch_and_sub_4(volatile void *, unsigned int);
extern unsigned int __sync_fetch_and_and_4(volatile void *, unsigned int);
extern unsigned int __sync_fetch_and_or_4(volatile void *, unsigned int);
extern unsigned int __sync_fetch_and_xor_4(volatile void *, unsigned int);
extern unsigned long long __sync_fetch_and_add_8(volatile void *, unsigned long long);
extern unsigned long long __sync_fetch_and_sub_8(volatile void *, unsigned long long);
extern unsigned long long __sync_fetch_and_and_8(volatile void *, unsigned long long);
extern unsigned long long __sync_fetch_and_or_8(volatile void *, unsigned long long);
extern unsigned long long __sync_fetch_and_xor_8(volatile void *, unsigned long long);

static __always_inline int arch_atomic_read(const atomic_t *v)
{
	return READ_ONCE(v->counter);
}
static __always_inline void arch_atomic_set(atomic_t *v, int i)
{
	WRITE_ONCE(v->counter, i);
}

#define arch_atomic_add(i, v) ({ (void)__sync_fetch_and_add_4(&(v)->counter, (i)); })
#define arch_atomic_sub(i, v) ({ (void)__sync_fetch_and_sub_4(&(v)->counter, (i)); })
#define arch_atomic_and(i, v) ({ (void)__sync_fetch_and_and_4(&(v)->counter, (i)); })
#define arch_atomic_or(i, v) ({ (void)__sync_fetch_and_or_4(&(v)->counter, (i)); })
#define arch_atomic_xor(i, v) ({ (void)__sync_fetch_and_xor_4(&(v)->counter, (i)); })

#define arch_atomic_fetch_add(i, v) ((int)__sync_fetch_and_add_4(&(v)->counter, (i)))
#define arch_atomic_fetch_add_relaxed(i, v) arch_atomic_fetch_add((i), (v))
#define arch_atomic_fetch_sub(i, v) ((int)__sync_fetch_and_sub_4(&(v)->counter, (i)))
#define arch_atomic_fetch_sub_relaxed(i, v) arch_atomic_fetch_sub((i), (v))
#define arch_atomic_fetch_and(i, v) ((int)__sync_fetch_and_and_4(&(v)->counter, (i)))
#define arch_atomic_fetch_and_relaxed(i, v) arch_atomic_fetch_and((i), (v))
#define arch_atomic_fetch_or(i, v) ((int)__sync_fetch_and_or_4(&(v)->counter, (i)))
#define arch_atomic_fetch_or_relaxed(i, v) arch_atomic_fetch_or((i), (v))
#define arch_atomic_fetch_xor(i, v) ((int)__sync_fetch_and_xor_4(&(v)->counter, (i)))
#define arch_atomic_fetch_xor_relaxed(i, v) arch_atomic_fetch_xor((i), (v))

static __always_inline int arch_atomic_add_return(int i, atomic_t *v)
{
	return (int)((unsigned int)arch_atomic_fetch_add(i, v) + (unsigned int)i);
}
#define arch_atomic_add_return arch_atomic_add_return
#define arch_atomic_add_return_relaxed(i, v) arch_atomic_add_return((i), (v))
static __always_inline int arch_atomic_sub_return(int i, atomic_t *v)
{
	return (int)((unsigned int)arch_atomic_fetch_sub(i, v) - (unsigned int)i);
}
#define arch_atomic_sub_return arch_atomic_sub_return
#define arch_atomic_sub_return_relaxed(i, v) arch_atomic_sub_return((i), (v))

static __always_inline int arch_atomic_fetch_add_unless(atomic_t *v, int a, int u)
{
	int prev = arch_atomic_read(v);
	if (prev != u)
		arch_atomic_set(v, (int)((unsigned int)prev + (unsigned int)a));
	return prev;
}
#define arch_atomic_fetch_add_unless arch_atomic_fetch_add_unless

static __always_inline bool arch_atomic_inc_unless_negative(atomic_t *v)
{
	int prev = arch_atomic_read(v);
	if (prev >= 0)
		arch_atomic_set(v, (int)((unsigned int)prev + (unsigned int)1));
	return prev >= 0;
}
#define arch_atomic_inc_unless_negative arch_atomic_inc_unless_negative

static __always_inline bool arch_atomic_dec_unless_positive(atomic_t *v)
{
	int prev = arch_atomic_read(v);
	if (prev <= 0)
		arch_atomic_set(v, (int)((unsigned int)prev - (unsigned int)1));
	return prev <= 0;
}
#define arch_atomic_dec_unless_positive arch_atomic_dec_unless_positive

static __always_inline int arch_atomic_dec_if_positive(atomic_t *v)
{
	int prev = arch_atomic_read(v);
	if (prev > 0)
		arch_atomic_set(v, (int)((unsigned int)prev - (unsigned int)1));
	return (int)((unsigned int)prev - 1);
}
#define arch_atomic_dec_if_positive arch_atomic_dec_if_positive

static __always_inline int arch_atomic_xchg(atomic_t *v, int n)
{
	return arch_xchg(&v->counter, n);
}
#define arch_atomic_xchg arch_atomic_xchg

static __always_inline int arch_atomic_cmpxchg(atomic_t *v, int o, int n)
{
	return arch_cmpxchg(&v->counter, o, n);
}
#define arch_atomic_cmpxchg arch_atomic_cmpxchg

static __always_inline bool arch_atomic_try_cmpxchg(atomic_t *v, int *old, int n)
{
	return arch_try_cmpxchg(&v->counter, old, n);
}
#define arch_atomic_try_cmpxchg arch_atomic_try_cmpxchg

/* arch_atomic64_* are always provided directly (the future copyspace
 * Kconfig will leave CONFIG_GENERIC_ATOMIC64 unset); the generic
 * lib/atomic64.c spinlock implementation is not used. */
#ifndef CONFIG_64BIT
typedef struct {
	s64 counter;
} atomic64_t;
#endif
#define ATOMIC64_INIT(i) { (i) }
static __always_inline s64 arch_atomic64_read(const atomic64_t *v)
{
	return READ_ONCE(v->counter);
}
static __always_inline void arch_atomic64_set(atomic64_t *v, s64 i)
{
	WRITE_ONCE(v->counter, i);
}

#define arch_atomic64_add(i, v) ({ (void)__sync_fetch_and_add_8(&(v)->counter, (i)); })
#define arch_atomic64_sub(i, v) ({ (void)__sync_fetch_and_sub_8(&(v)->counter, (i)); })
#define arch_atomic64_and(i, v) ({ (void)__sync_fetch_and_and_8(&(v)->counter, (i)); })
#define arch_atomic64_or(i, v) ({ (void)__sync_fetch_and_or_8(&(v)->counter, (i)); })
#define arch_atomic64_xor(i, v) ({ (void)__sync_fetch_and_xor_8(&(v)->counter, (i)); })

#define arch_atomic64_fetch_add(i, v) ((s64)__sync_fetch_and_add_8(&(v)->counter, (i)))
#define arch_atomic64_fetch_add_relaxed(i, v) arch_atomic64_fetch_add((i), (v))
#define arch_atomic64_fetch_sub(i, v) ((s64)__sync_fetch_and_sub_8(&(v)->counter, (i)))
#define arch_atomic64_fetch_sub_relaxed(i, v) arch_atomic64_fetch_sub((i), (v))
#define arch_atomic64_fetch_and(i, v) ((s64)__sync_fetch_and_and_8(&(v)->counter, (i)))
#define arch_atomic64_fetch_and_relaxed(i, v) arch_atomic64_fetch_and((i), (v))
#define arch_atomic64_fetch_or(i, v) ((s64)__sync_fetch_and_or_8(&(v)->counter, (i)))
#define arch_atomic64_fetch_or_relaxed(i, v) arch_atomic64_fetch_or((i), (v))
#define arch_atomic64_fetch_xor(i, v) ((s64)__sync_fetch_and_xor_8(&(v)->counter, (i)))
#define arch_atomic64_fetch_xor_relaxed(i, v) arch_atomic64_fetch_xor((i), (v))

static __always_inline s64 arch_atomic64_add_return(s64 i, atomic64_t *v)
{
	return (s64)((u64)arch_atomic64_fetch_add(i, v) + (u64)i);
}
#define arch_atomic64_add_return arch_atomic64_add_return
#define arch_atomic64_add_return_relaxed(i, v) arch_atomic64_add_return((i), (v))
static __always_inline s64 arch_atomic64_sub_return(s64 i, atomic64_t *v)
{
	return (s64)((u64)arch_atomic64_fetch_sub(i, v) - (u64)i);
}
#define arch_atomic64_sub_return arch_atomic64_sub_return
#define arch_atomic64_sub_return_relaxed(i, v) arch_atomic64_sub_return((i), (v))

static __always_inline s64 arch_atomic64_fetch_add_unless(atomic64_t *v, s64 a, s64 u)
{
	s64 prev = arch_atomic64_read(v);
	if (prev != u)
		arch_atomic64_set(v, (s64)((u64)prev + (u64)a));
	return prev;
}
#define arch_atomic64_fetch_add_unless arch_atomic64_fetch_add_unless

static __always_inline bool arch_atomic64_inc_unless_negative(atomic64_t *v)
{
	s64 prev = arch_atomic64_read(v);
	if (prev >= 0)
		arch_atomic64_set(v, (s64)((u64)prev + (u64)1));
	return prev >= 0;
}
#define arch_atomic64_inc_unless_negative arch_atomic64_inc_unless_negative

static __always_inline bool arch_atomic64_dec_unless_positive(atomic64_t *v)
{
	s64 prev = arch_atomic64_read(v);
	if (prev <= 0)
		arch_atomic64_set(v, (s64)((u64)prev - (u64)1));
	return prev <= 0;
}
#define arch_atomic64_dec_unless_positive arch_atomic64_dec_unless_positive

static __always_inline s64 arch_atomic64_dec_if_positive(atomic64_t *v)
{
	s64 prev = arch_atomic64_read(v);
	if (prev > 0)
		arch_atomic64_set(v, (s64)((u64)prev - (u64)1));
	return (s64)((u64)prev - 1);
}
#define arch_atomic64_dec_if_positive arch_atomic64_dec_if_positive

static __always_inline s64 arch_atomic64_xchg(atomic64_t *v, s64 n)
{
	return arch_xchg(&v->counter, n);
}
#define arch_atomic64_xchg arch_atomic64_xchg

static __always_inline s64 arch_atomic64_cmpxchg(atomic64_t *v, s64 o, s64 n)
{
	return arch_cmpxchg(&v->counter, o, n);
}
#define arch_atomic64_cmpxchg arch_atomic64_cmpxchg

static __always_inline bool arch_atomic64_try_cmpxchg(atomic64_t *v, s64 *old, s64 n)
{
	return arch_try_cmpxchg(&v->counter, old, n);
}
#define arch_atomic64_try_cmpxchg arch_atomic64_try_cmpxchg

#endif /* _ASM_COPYSPACE_ATOMIC_H */
