#include "pf_all.h"

void *pfSetByteMemory(void *, cell_t, cell_t);
void *pfCopyByteMemory(void *, const void *, cell_t);

#ifdef MEMORY_BASELINE
#define tested_fill pfSetByteMemory
#define tested_copy pfCopyByteMemory
#else
#define tested_fill pfSetMemory
#define tested_copy pfCopyMemory
#endif

static uint8_t actual[128] __attribute__((aligned(16)));
static uint8_t reference[128] __attribute__((aligned(16)));
static uint8_t bulk_source[4096] __attribute__((aligned(16)));
static uint8_t bulk_target[4096] __attribute__((aligned(16)));
static uint32_t checks;

static void reset(void)
{
    for(unsigned i=0; i<sizeof actual; ++i)
        actual[i] = reference[i] = (uint8_t)(i*13+checks);
}

static int equal(void)
{
    for(unsigned i=0; i<sizeof actual; ++i)
        if(actual[i] != reference[i]) return 0;
    ++checks;
    return 1;
}

static int fill_case(unsigned offset, int count, int value)
{
    reset();
    if(tested_fill(actual+16+offset, value, count) != actual+16+offset) return 0;
    pfSetByteMemory(reference+16+offset, value, count);
    return equal();
}

static int copy_case(unsigned src, unsigned dst, int count)
{
    reset();
    if(tested_copy(actual+16+dst, actual+16+src, count) != actual+16+dst) return 0;
    pfCopyByteMemory(reference+16+dst, reference+16+src, count);
    return equal();
}

int main(void)
{
#ifdef MEMORY_GUEST
    static const int lengths[] = {0,1,3,4,5,7,8,17};
    static const int values[] = {-1,0,255,0x123};
    for(unsigned offset=0; offset<4; ++offset)
        for(unsigned n=0; n<8; ++n)
            for(unsigned v=0; v<4; ++v)
                if(!fill_case(offset, lengths[n], values[v])) return 1;
    for(unsigned src=0; src<4; ++src)
        for(unsigned dst=0; dst<4; ++dst)
            if(!copy_case(src, dst, lengths[(src*4+dst)%8])) return 2;
    if(!copy_case(0,0,-1) || !copy_case(0,4,31) || !copy_case(4,0,31)
       || !copy_case(0,8,31) || !copy_case(8,0,31)) return 3;
#else
    static const int values[] = {-256,-1,0,1,127,128,255,256,0x123};
    for(unsigned offset=0; offset<16; ++offset)
        for(int n=-1; n<=64; ++n)
            for(unsigned v=0; v<9; ++v)
                if(!fill_case(offset,n,values[v])) return 1;
    for(unsigned src=0; src<16; ++src)
        for(unsigned dst=0; dst<16; ++dst)
            for(int n=-1; n<=64; ++n)
                if(!copy_case(src,dst,n)) return 2;
#endif
    tested_fill(bulk_source,0xa5,sizeof bulk_source);
    tested_fill(bulk_target,0,sizeof bulk_target);
    tested_copy(bulk_target,bulk_source,sizeof bulk_source);
    for(unsigned i=0; i<sizeof bulk_target; ++i)
        if(bulk_target[i] != 0xa5) return 4;
    ++checks;
    uint32_t result[2] = {7,checks};
    return cs_write(result,sizeof result) == sizeof result ? 0 : 5;
}
