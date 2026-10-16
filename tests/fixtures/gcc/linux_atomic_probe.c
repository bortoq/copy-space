#include <linux/atomic.h>
#include <linux/bitops.h>

static atomic_t a;
static atomic64_t b;
static unsigned long map[2];

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
	return passed;
}
