/* SPDX-License-Identifier: GPL-2.0 */
#include <lib/string.c>
#include <lib/ctype.c>
#ifdef CS_GCC_TEST_EXTERNAL_LIBGCC
extern u64 __muldi3(u64, u64);
#else
#include "muldi3.c"
#endif

_Static_assert(sizeof(void *) == 4 && sizeof(long) == 4 && sizeof(u64) == 8,
               "copyspace kernel ABI");
_Static_assert(PAGE_SIZE == 4096 && PAGE_MASK == ~4095UL, "logical page geometry");

static unsigned warnings;
void warn_slowpath_fmt(const char *file, int line, unsigned taint,
                       const char *format, ...)
{
    if (!file || line <= 0 || taint != TAINT_WARN || format)
        __builtin_trap();
    ++warnings;
}

unsigned value(unsigned a, unsigned b)
{
    char buffer[64];
    char overlap[8] = "abcdefg";
    char source[16] __attribute__((aligned(4)));
    char destination[16] __attribute__((aligned(4)));
    u16 halves[3] = {0};
    u32 words[3] = {0};
    u64 doubles[3] = {0};
    char tokens[] = "a::b", *next = tokens;
    const char *text = "abcabc";

    if (strcpy(buffer, "ab") != buffer || strcat(buffer, "cd") != buffer ||
        strcmp(buffer, "abcd") || strlen(buffer) != 4)
        return 1001;
    if (strlcat(buffer, "efgh", 7) != 8 || strcmp(buffer, "abcdef"))
        return 1002;
    if (memmove(overlap + 2, overlap, 5) != overlap + 2 ||
        memcmp(overlap, "ababcde", 7))
        return 1003;
    if (memmove(overlap, overlap + 2, 5) != overlap ||
        memcmp(overlap, "abcde", 5))
        return 1004;
    if (memset16(halves, 0x1234, 2) != halves || halves[0] != 0x1234 ||
        halves[1] != 0x1234 || halves[2])
        return 1005;
    if (memset32(words, 0xabcdef01, 2) != words || words[0] != 0xabcdef01 ||
        words[1] != 0xabcdef01 || words[2])
        return 1006;
    if (memset64(doubles, 0x0123456789abcdefULL, 2) != doubles ||
        doubles[0] != 0x0123456789abcdefULL ||
        doubles[1] != 0x0123456789abcdefULL || doubles[2])
        return 1007;
    for (unsigned length = 0; length < 13; ++length) {
        memset(source, 'x', sizeof(source));
        source[length] = 0;
        memset(destination, 0x7f, sizeof(destination));
        if (sized_strscpy(destination, source, sizeof(destination)) != length ||
            destination[length] || memcmp(source, destination, length))
            return 1010 + length;
    }
    if (sized_strscpy(destination + 1, "hello", 4) != -E2BIG ||
        strcmp(destination + 1, "hel") || sized_strscpy(NULL, NULL, 0) != -E2BIG)
        return 1030;
    if (strcasecmp("AbCd", "aBcD") || strncasecmp("aBzz", "Abxx", 2))
        return 1031;
    if (strstr(text, "cab") != text + 2 || strnstr(text, "cab", 4) != NULL ||
        strchr(text, 'b') != text + 1 || strrchr(text, 'b') != text + 4)
        return 1032;
    if (strcmp(strsep(&next, ":"), "a") || strcmp(strsep(&next, ":"), "") ||
        strcmp(strsep(&next, ":"), "b") || next || strsep(&next, ":"))
        return 1033;
    if (memchr(text, 'c', 6) != text + 2 || memscan((void *)text, 'z', 6) != text + 6 ||
        strnlen(text, 3) != 3)
        return 1034;
    memset(buffer, a + 87, sizeof(buffer));
    buffer[45] = a + 86;
    if (memchr_inv(buffer, a + 87, sizeof(buffer)) != buffer + 45)
        return 1035;
    return 200 + a + b;
}

unsigned fatal(unsigned a, unsigned b)
{
    char destination[5] = "abcd";
    return strlcat(destination, "x", 4);
}

unsigned warning_once(unsigned a, unsigned b)
{
    if (sized_strscpy(NULL, NULL, (size_t)INT_MAX + 1) != -E2BIG ||
        sized_strscpy(NULL, NULL, (size_t)INT_MAX + 1) != -E2BIG)
        return 999;
    return warnings;
}

unsigned multiplication(unsigned a, unsigned b)
{
    static const volatile u64 cases[][3] = {
        {0, 0, 0},
        {0xffffffffULL, 0xffffffffULL, 0xfffffffe00000001ULL},
        {0x100000001ULL, 0x100000001ULL, 0x200000001ULL},
        {0xffffffffffffffffULL, 0xffffffffffffffffULL, 1},
        {0x8000000000000000ULL, 3, 0x8000000000000000ULL},
        {0xffffffff00000000ULL, 0xffffffffULL, 0x100000000ULL},
        {0xffff0000ULL, 0xffff0000ULL, 0xfffe000100000000ULL},
        {0x80008000ULL, 0x80008000ULL, 0x4000800040000000ULL}
    };
    u64 (*volatile multiply)(u64, u64) = __muldi3;
    for (unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i)
        if (multiply(cases[i][0], cases[i][1]) != cases[i][2])
            return 900 + i;
    return 8;
}

unsigned bit_operations(unsigned a, unsigned b)
{
    unsigned long bitmap[2] = {0};
    unsigned bit = a + 32;
    __set_bit(bit, bitmap);
    if (!test_bit(bit, bitmap) || bitmap[0] || bitmap[1] != 8 ||
        !__test_and_set_bit(bit, bitmap))
        return 1101;
    __clear_bit(bit, bitmap);
    if (test_bit(bit, bitmap) || bitmap[1])
        return 1102;
    __change_bit(b + 32, bitmap);
    if (!test_bit_acquire(b + 32, bitmap) || bitmap[1] != 16 ||
        !__test_and_clear_bit(b + 32, bitmap) || bitmap[1])
        return 1103;
    for (unsigned i = 0; i < 32; ++i) {
        volatile unsigned long word = 1UL << i;
        if (__ffs(word) != i || __fls(word) != i || ffs(word) != i + 1 ||
            fls(word) != i + 1 || fls64((u64)word << 32) != i + 33 ||
            ffz(~word) != i)
            return 1110 + i;
    }
    if (ffs(0) || fls(0) || fls64(0))
        return 1150;
    WRITE_ONCE(bitmap[0], a);
    mb();
    rmb();
    wmb();
    nop();
    if (READ_ONCE(bitmap[0]) != a)
        return 1151;
    return 32;
}

unsigned argument_home(unsigned a, unsigned b)
{
    volatile unsigned *left = &a, *right = &b;
    *left += b;
    return *left + *right;
}

unsigned variadic(unsigned count, ...)
{
    unsigned result = 0;
    __builtin_va_list ap;
    __builtin_va_start(ap, count);
    for (unsigned i = 0; i < count; ++i)
        result += __builtin_va_arg(ap, unsigned);
    __builtin_va_end(ap);
    return result;
}

static __attribute__((__noinline__, __noipa__)) unsigned sum_eight(unsigned a, unsigned b,
        unsigned c, unsigned d, unsigned e, unsigned f, unsigned g, unsigned h)
{
    return a + b + c + d + e + f + g + h;
}

unsigned stack_arguments(unsigned a, unsigned b)
{
    return sum_eight(a, b, 5, 6, 7, 8, 9, 10);
}

unsigned variadic_call(unsigned a, unsigned b)
{
    unsigned (*volatile sum)(unsigned, ...) = variadic;
    return sum(7, a, b, 5, 6, 7, 8, 9);
}
