#include "copy_emit.h"
#include <string.h>
#ifdef __riscv
#include "copy_space.h"
#else
#include <stdio.h>
static int cs_read(void *p, unsigned n) { return (int)fread(p,1,n,stdin); }
static int cs_write(const void *p, unsigned n) { return (int)fwrite(p,1,n,stdout); }
#endif
#ifndef CS_COPY_LAYER
#define CS_COPY_LAYER 0
#endif
#ifndef CS_COPY_RESULT
#define CS_COPY_RESULT 49216
#endif
#if CS_COPY_LAYER
#define CS_COPY_OUTPUT_LAYER 98304
#define CS_COPY_ZERO_LAYER 147456
static unsigned char data[32768];
#else
#define CS_COPY_OUTPUT_LAYER 65536
#define CS_COPY_ZERO_LAYER 98304
static unsigned char data[16384];
#endif
int main(void)
{
    unsigned char input[8];
    unsigned read=0;
    while (read<8) {
        int n=cs_read(input+read,8-read);
        if (n<=0 || (unsigned)n>8-read) return 1;
        read+=(unsigned)n;
    }
    uint32_t a=0,b=0;
    for (unsigned i=0;i<4;++i) { a|=(uint32_t)input[i]<<(8*i); b|=(uint32_t)input[i+4]<<(8*i); }
    struct cs_copy_image image;
    if (cs_copy_image_init(&image,data,sizeof(data),24,CS_COPY_LAYER) ||
        cs_copy_constant(&image,49152,32,a) || cs_copy_constant(&image,49184,32,b) ||
        cs_copy_add32(&image,CS_COPY_RESULT,49152,49184,32800,49250,49248)) return 2;
    for (unsigned i=0;i<32;++i)
        if (cs_copy_emit(&image,1,51000+(i/8)*8+7-(i%8),CS_COPY_RESULT+i)) return 3;
    if (cs_copy_row(&image,255,image.layer_bits,0,CS_COPY_OUTPUT_LAYER) ||
        cs_copy_image_init(&image,data,sizeof(data),24,CS_COPY_OUTPUT_LAYER) ||
        cs_copy_row(&image,2,32,51000,52000) ||
        cs_copy_row(&image,255,image.layer_bits,0,CS_COPY_ZERO_LAYER)) return 4;
#if CS_COPY_LAYER
    if (cs_copy_image_init(&image,data,sizeof(data),24,0) ||
        cs_copy_row(&image,255,image.layer_bits,0,CS_COPY_LAYER)) return 4;
#endif
    unsigned written=0;
    while (written<sizeof(data)) {
        int n=cs_write(data+written,sizeof(data)-written);
        if (n<=0 || (unsigned)n>sizeof(data)-written) return 5;
        written+=(unsigned)n;
    }
    return 0;
}
