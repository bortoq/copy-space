/* Preserve the pinned byte implementation as the reference and fallback.
 * This library is part of the guest, not of the host space emulator. */
#define pfSetMemory pfSetByteMemory
#define pfCopyMemory pfCopyByteMemory
#include "../../third_party/pforth/csrc/pf_clib.c"
#undef pfSetMemory
#undef pfCopyMemory

void *pfSetMemory(void *destination, cell_t byte, cell_t count)
{
    uint8_t *out = destination;
    uint8_t value = (uint8_t)byte;
    if(count <= 0) return destination;
    while(count && ((uintptr_t)out & 3))
    {
        *out++ = value;
        --count;
    }
    uint32_t word = value;
    word |= word << 8;
    word |= word << 16;
    while(count >= 4)
    {
        *(uint32_t *)out = word;
        out += 4;
        count -= 4;
    }
    while(count-- > 0) *out++ = value;
    return destination;
}

void *pfCopyMemory(void *destination, const void *source, cell_t count)
{
    uint8_t *out = destination;
    const uint8_t *in = source;
    if(count <= 0) return destination;
    if(((uintptr_t)out ^ (uintptr_t)in) & 3)
        return pfCopyByteMemory(destination, source, count);
    while(count && ((uintptr_t)out & 3))
    {
        *out++ = *in++;
        --count;
    }
    /* Co-aligned overlapping pointers differ by whole words. A forward
     * word copy therefore preserves the original forward byte propagation. */
    while(count >= 4)
    {
        *(uint32_t *)out = *(const uint32_t *)in;
        out += 4;
        in += 4;
        count -= 4;
    }
    while(count-- > 0) *out++ = *in++;
    return destination;
}
