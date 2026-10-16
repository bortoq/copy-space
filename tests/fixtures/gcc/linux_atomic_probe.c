#include <linux/atomic.h>
#include <linux/bitops.h>
/* Public arch headers must also tolerate repeated inclusion. */
#include <asm/bitops.h>
#include <asm/cmpxchg.h>

static atomic_t a;
static atomic64_t b;
static unsigned long map[2];
static unsigned pointer_calls, old_calls, value_calls;
static u64 wide;
static u64 expected;

static __attribute__((__noinline__, __noipa__)) u64 *wide_ptr(void)
{ ++pointer_calls; return &wide; }
static __attribute__((__noinline__, __noipa__)) u64 *old_ptr(void)
{ ++old_calls; return &expected; }
static __attribute__((__noinline__, __noipa__)) int increment(void)
{ ++value_calls; return 3; }
static __attribute__((__noinline__, __noipa__)) signed char *byte_ptr(signed char *p)
{ ++pointer_calls; return p; }

unsigned value(void)
{
	unsigned passed = 0;

	atomic_set(&a, 10);
	passed += atomic_read(&a) == 10;
	passed += atomic_add_return(5, &a) == 15;
	passed += atomic_fetch_sub(3, &a) == 15;
	passed += atomic_read(&a) == 12;
	passed += atomic_cmpxchg(&a, 12, 20) == 12;
	passed += atomic_read(&a) == 20;
	passed += arch_xchg(&a.counter, 7) == 20;
	passed += atomic_read(&a) == 7;
	passed += atomic_dec_if_positive(&a) == 6;
	passed += atomic_read(&a) == 6;

	atomic64_set(&b, 100);
	passed += atomic64_read(&b) == 100;
	passed += atomic64_add_return(23, &b) == 123;
	passed += arch_cmpxchg64(&b.counter, 123, 200) == 123;
	passed += atomic64_read(&b) == 200;

	set_bit(5, map);
	passed += map[0] == 32U;
	passed += test_and_set_bit(5, map) == 1;
	passed += test_and_clear_bit(5, map) == 1;
	passed += map[0] == 0U;
	set_bit(33, map);
	passed += map[1] == 2U;
	clear_bit(33, map);
	passed += map[1] == 0U;

	/* Values above UINT32_MAX must survive a 32-bit target ABI. */
	wide = 0x123456789abcdef0ULL;
	passed += arch_xchg(&wide, 0xfedcba9876543210ULL) == 0x123456789abcdef0ULL;
	passed += wide == 0xfedcba9876543210ULL;
	passed += arch_cmpxchg64(&wide, 0xfedcba9876543210ULL,
				0x1122334455667788ULL) == 0xfedcba9876543210ULL;
	passed += wide == 0x1122334455667788ULL;
	passed += arch_cmpxchg64(&wide, 0x1122334455667789ULL, 0ULL) == 0x1122334455667788ULL;
	passed += wide == 0x1122334455667788ULL;

	/* Signed sub-word writes must preserve surrounding bytes. */
	union { u32 word; signed char bytes[4]; short halves[2]; } narrow;
	narrow.word = 0x12345678U;
	passed += arch_xchg(&narrow.bytes[1], -1) == 0x56;
	passed += narrow.word == 0x1234ff78U;
	passed += arch_xchg(&narrow.halves[0], -2) == (short)0xff78;
	passed += narrow.word == 0x1234fffeU;
	passed += arch_cmpxchg(&narrow.bytes[0], -2, -3) == -2;
	passed += narrow.word == 0x1234fffdU;
	pointer_calls = 0;
	passed += arch_xchg(byte_ptr(&narrow.bytes[1]), -4) == -1;
	passed += pointer_calls == 1 && narrow.word == 0x1234fcfdU;
	pointer_calls = 0;
	passed += arch_cmpxchg(byte_ptr(&narrow.bytes[1]), -4, -5) == -4;
	passed += pointer_calls == 1 && narrow.word == 0x1234fbfdU;

	/* Public operations evaluate every supplied expression once. */
	pointer_calls = old_calls = 0;
	wide = 9; expected = 8;
	passed += !arch_try_cmpxchg(wide_ptr(), old_ptr(), 11ULL);
	passed += pointer_calls == 1 && old_calls == 1;
	passed += expected == 9 && wide == 9;
	pointer_calls = old_calls = 0;
	passed += arch_try_cmpxchg(wide_ptr(), old_ptr(), 0xaabbccdd12345678ULL);
	passed += pointer_calls == 1 && old_calls == 1;
	passed += wide == 0xaabbccdd12345678ULL;
	pointer_calls = 0;
	passed += arch_cmpxchg64(wide_ptr(), 0xaabbccdd12345678ULL, 5ULL) == 0xaabbccdd12345678ULL;
	passed += pointer_calls == 1 && wide == 5;

	atomic_set(&a, 1); value_calls = 0;
	passed += arch_atomic_add_return(increment(), &a) == 4;
	passed += value_calls == 1 && atomic_read(&a) == 4;
	value_calls = 0;
	passed += arch_atomic_sub_return(increment(), &a) == 1;
	passed += value_calls == 1 && atomic_read(&a) == 1;
	atomic64_set(&b, 1); value_calls = 0;
	passed += arch_atomic64_add_return(increment(), &b) == 4;
	passed += value_calls == 1 && atomic64_read(&b) == 4;
	value_calls = 0;
	passed += arch_atomic64_sub_return(increment(), &b) == 1;
	passed += value_calls == 1 && atomic64_read(&b) == 1;

	/* Fetch and return APIs have signed int/s64 results. */
	atomic_set(&a, -3);
	passed += arch_atomic_fetch_add(1, &a) < 0;
	passed += arch_atomic_sub_return(3, &a) < 0;
	atomic64_set(&b, -3);
	passed += arch_atomic64_fetch_add(1, &b) < 0;
	passed += arch_atomic64_sub_return(3, &b) < 0;
	atomic_set(&a, 0x7fffffff);
	passed += arch_atomic_add_return(1, &a) == (-0x7fffffff - 1);
	atomic64_set(&b, 0x7fffffffffffffffLL);
	passed += arch_atomic64_add_return(1, &b) == (-0x7fffffffffffffffLL - 1);
	void *pointer = &a;
	passed += arch_xchg(&pointer, (void *)&b) == (void *)&a;
	passed += pointer == (void *)&b;
	passed += arch_cmpxchg(&pointer, (void *)&b, (void *)&a) == (void *)&b;
	passed += pointer == (void *)&a;
	return passed;
}
