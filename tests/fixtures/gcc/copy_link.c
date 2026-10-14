#include "copy_link.h"
#ifdef __riscv
#include "copy_space.h"
#else
#include <stdio.h>
static int cs_read(void *p, unsigned n) { return (int)fread(p,1,n,stdin); }
static int cs_write(const void *p, unsigned n) { return (int)fwrite(p,1,n,stdout); }
#endif
static unsigned char image[32768];
static char assembly[8192];
#ifndef CS_COPY_RESULT_ADDRESS_BITS
#define CS_COPY_RESULT_ADDRESS_BITS 24
#endif
int main(void)
{
    unsigned size=0;
    for (;;) {
        int n=cs_read(assembly+size,sizeof(assembly)-size);
        if (n<0 || (unsigned)n>sizeof(assembly)-size) return 1;
        if (!n) break;
        size+=(unsigned)n;
        if (size==sizeof(assembly)) return 1;
    }
    const uint32_t arguments[]={3,4};
    struct cs_copy_link_error error;
    if (cs_copy_link_leaf(image,sizeof(image),CS_COPY_RESULT_ADDRESS_BITS,assembly,size,"value",arguments,2,&error)) return 2;
    unsigned written=0;
    while (written<sizeof(image)) {
        int n=cs_write(image+written,sizeof(image)-written);
        if (n<=0 || (unsigned)n>sizeof(image)-written) return 3;
        written+=(unsigned)n;
    }
    return 0;
}
