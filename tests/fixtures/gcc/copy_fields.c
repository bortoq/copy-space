#include "copy_emit.h"
#include <string.h>
#ifdef __riscv
#include "copy_space.h"
#else
#include <stdio.h>
#ifndef CS_FIELD_EXHAUSTIVE
static int cs_write(const void *p, unsigned n) { return (int)fwrite(p,1,n,stdout); }
#endif
#endif
static unsigned char data[4098];
int main(void)
{
    struct cs_copy_image image;
    if (cs_copy_image_init(&image,data+1,4096,24,0)) return 1;
#ifdef CS_FIELD_EXHAUSTIVE
    unsigned char expected[4096];
    memset(data,0xa5,sizeof(data));memset(expected,0xa5,sizeof(expected));
    unsigned cases=0;
    for (unsigned offset=0;offset<8;++offset) for (unsigned width=1;width<=32;++width) {
        uint32_t seed=0x12345678;
        for (unsigned sample=0;sample<68;++sample) {
            uint32_t value;
            if (sample<32) value=UINT32_C(1)<<sample;
            else if (sample==32) value=0;
            else if (sample==33) value=UINT32_MAX;
            else if (sample==34) value=0xaaaaaaaa;
            else if (sample==35) value=0x55555555;
            else { seed=seed*1664525u+1013904223u;value=seed; }
            uint32_t at=32704+offset;
            memset(data+1+4080,0xa5,16);memset(expected+4080,0xa5,16);
            for (unsigned bit=0;bit<width;++bit) {
                unsigned char mask=(unsigned char)(1u<<(7-((at+bit)&7)));
                if ((value>>bit)&1) expected[(at+bit)/8]|=mask;
                else expected[(at+bit)/8]&=(unsigned char)~mask;
            }
            if (cs_copy_constant(&image,at,width,value) || memcmp(data+1,expected,4096) || data[0]!=0xa5 || data[4097]!=0xa5) return 2;
            ++cases;
        }
    }
    if (cs_copy_constant(&image,32767,2,3)!=-1 || cs_copy_constant(&image,0,0,0)!=-1 || cs_copy_constant(&image,0,33,0)!=-1) return 3;
    printf("OK %u bit fields and preserved neighbours\n",cases);
#else
    memset(data+1+3750,0xa5,64);
    for (unsigned i=0;i<64;++i) {
        uint32_t value=0x9e3779b9u^((i<<24)|(i<<16)|(i<<8)|i);
        if (cs_copy_constant(&image,30000+(i&7)+(i>>3)*40,1+(i&31),value)) return 2;
    }
    unsigned written=0;
    while (written<64) {
        int n=cs_write(data+1+3750+written,64-written);
        if (n<=0 || (unsigned)n>64-written) return 3;
        written+=(unsigned)n;
    }
#endif
    return 0;
}
