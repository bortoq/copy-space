#include <stdint.h>

/* GNU i386 reference needs a freestanding division runtime. Use a shifted
 * divisor, independently of the target's restoring division and cell helper. */
static uint64_t reference_div(uint64_t n, uint64_t d, uint64_t *remainder)
{
    uint64_t q=0, bit=1;
    if (!d) __builtin_trap();
    while (d <= n && !(d >> 63)) { d <<= 1; bit <<= 1; }
    do {
        if (n >= d) { n -= d; q |= bit; }
        d >>= 1; bit >>= 1;
    } while (bit);
    if (remainder) *remainder=n;
    return q;
}
uint64_t __udivdi3(uint64_t n, uint64_t d) { return reference_div(n, d, 0); }
uint64_t __umoddi3(uint64_t n, uint64_t d)
{
    uint64_t r;
    reference_div(n, d, &r);
    return r;
}
int64_t __divdi3(int64_t n, int64_t d)
{
    uint64_t q=reference_div(n < 0 ? -(uint64_t)n : (uint64_t)n,
                             d < 0 ? -(uint64_t)d : (uint64_t)d, 0);
    return (int64_t)((n < 0) != (d < 0) ? -q : q);
}
int64_t __moddi3(int64_t n, int64_t d)
{
    uint64_t r;
    reference_div(n < 0 ? -(uint64_t)n : (uint64_t)n,
                  d < 0 ? -(uint64_t)d : (uint64_t)d, &r);
    return (int64_t)(n < 0 ? -r : r);
}
