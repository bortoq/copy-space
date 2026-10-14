#include <errno.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifdef __riscv
extern void *_sbrk(ptrdiff_t increment);
#endif

static int compare(const void *a, const void *b)
{
    unsigned x = *(const unsigned *)a, y = *(const unsigned *)b;
    return (x > y) - (x < y);
}

int main(void)
{
    unsigned a, b;
    if (scanf("%u %u", &a, &b) != 2) return 1;
    unsigned *values = calloc(16, sizeof(*values));
    if (!values) return 2;
    for (unsigned i = 0; i < 16; ++i) {
        if (values[i]) return 3;
        values[i] = 15 - i;
    }
    qsort(values, 16, sizeof(*values), compare);
    for (unsigned i = 0; i < 16; ++i) if (values[i] != i) return 4;
    unsigned *grown = realloc(values, 32 * sizeof(*values));
    if (!grown) return 5;
    for (unsigned i = 0; i < 16; ++i) if (grown[i] != i) return 6;
    void *aligned = malloc(33);
    if (!aligned || (uintptr_t)aligned % __alignof__(long double)) return 7;
    memset(aligned, 0x5a, 33);
    if (((unsigned char *)aligned)[32] != 0x5a) return 8;
#ifdef __riscv
    void *before = _sbrk(0);
    errno = 0;
    if (_sbrk(PTRDIFF_MAX) != (void *)-1 || errno != ENOMEM || _sbrk(0) != before) return 9;
    errno = 0;
    if (_sbrk(PTRDIFF_MIN) != (void *)-1 || errno != ENOMEM || _sbrk(0) != before) return 10;
#endif
    unsigned long long wide = (1ULL << 32) + a + b;
    int printed = printf("gcc-libc:%u:%u:%llu\n", a+b, grown[15], wide);
    if (printed <= 0 || fflush(stdout)) return 11;
    free(aligned);
    free(grown);
    return 0;
}
