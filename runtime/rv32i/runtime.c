#include "copy_space.h"
#include <stddef.h>

static int call(unsigned int operation, unsigned int argument,
                const void *buffer, unsigned int bytes)
{
    register unsigned int a0 __asm__("a0") = argument;
    register const void *a1 __asm__("a1") = buffer;
    register unsigned int a2 __asm__("a2") = bytes;
    register unsigned int a7 __asm__("a7") = operation;
    __asm__ volatile("ecall" : "+r"(a0) : "r"(a1), "r"(a2), "r"(a7) : "memory");
    return (int)a0;
}

int cs_read(void *buffer, unsigned int bytes)
{
    return call(63, 0, buffer, bytes);
}

int cs_write(const void *buffer, unsigned int bytes)
{
    return call(64, 1, buffer, bytes);
}

void cs_exit(int code)
{
    (void)call(93, (unsigned int)code, NULL, 0);
    for(;;)
        __asm__ volatile("");
}

/* Freestanding GCC may emit these calls even without libc. */
#ifndef CS_RUNTIME_EXTERNAL_MEMORY
void *memcpy(void *dst, const void *src, size_t bytes)
{
    unsigned char *out = dst;
    const unsigned char *in = src;
    size_t i;
    for(i = 0; i < bytes; ++i)
        out[i] = in[i];
    return dst;
}

void *memmove(void *dst, const void *src, size_t bytes)
{
    unsigned char *out = dst;
    const unsigned char *in = src;
    size_t i;
    if((unsigned long)dst <= (unsigned long)src)
        for(i = 0; i < bytes; ++i)
            out[i] = in[i];
    else
        for(i = bytes; i; --i)
            out[i-1] = in[i-1];
    return dst;
}

void *memset(void *dst, int value, size_t bytes)
{
    unsigned char *out = dst;
    size_t i;
    for(i = 0; i < bytes; ++i)
        out[i] = (unsigned char)value;
    return dst;
}

int memcmp(const void *a, const void *b, size_t bytes)
{
    const unsigned char *left = a, *right = b;
    size_t i;
    for(i = 0; i < bytes; ++i)
        if(left[i] != right[i])
            return (int)left[i] - (int)right[i];
    return 0;
}
#endif
