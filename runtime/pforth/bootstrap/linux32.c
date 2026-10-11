/* Build-time tool only: Linux i386 system calls without libc or libgcc.
 * It prepares a target-width dictionary; never linked into an RV32I image. */
#include "copy_space.h"
#include <stdint.h>

static int call(int number, int descriptor, const void *buffer, unsigned int bytes)
{
    int result;
    __asm__ volatile("int $0x80" : "=a"(result)
                     : "0"(number), "b"(descriptor), "c"(buffer), "d"(bytes) : "memory");
    return result;
}
int cs_read(void *buffer, unsigned int bytes) { return call(3, 0, buffer, bytes); }
int cs_write(const void *buffer, unsigned int bytes) { return call(4, 1, buffer, bytes); }
void cs_exit(int code)
{
    (void)call(1, code, 0, 0);
    for(;;) __asm__ volatile("");
}
extern int main(void);
__asm__(".global _start\n_start:\n andl $-16, %esp\n call main\n pushl %eax\n call cs_exit\n");

uint64_t __udivmoddi4(uint64_t n, uint64_t d, uint64_t *remainder)
{
    uint64_t q = 0, r = 0;
    if(!d) cs_exit(70);
    for(int i=63; i>=0; --i)
    {
        unsigned int carry = (unsigned int)(r >> 63);
        r = (r << 1) | ((n >> i) & 1);
        if(carry || r >= d) { r -= d; q |= (uint64_t)1 << i; }
    }
    if(remainder) *remainder = r;
    return q;
}
uint64_t __udivdi3(uint64_t n, uint64_t d) { return __udivmoddi4(n, d, 0); }
uint64_t __umoddi3(uint64_t n, uint64_t d)
{
    uint64_t r;
    (void)__udivmoddi4(n, d, &r);
    return r;
}
int64_t __divdi3(int64_t n, int64_t d)
{
    uint64_t q = __udivdi3(n < 0 ? -(uint64_t)n : (uint64_t)n,
                           d < 0 ? -(uint64_t)d : (uint64_t)d);
    return (int64_t)((n < 0) != (d < 0) ? -q : q);
}
int64_t __moddi3(int64_t n, int64_t d)
{
    uint64_t r = __umoddi3(n < 0 ? -(uint64_t)n : (uint64_t)n,
                           d < 0 ? -(uint64_t)d : (uint64_t)d);
    return (int64_t)(n < 0 ? -r : r);
}
