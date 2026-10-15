#include "copy_link.h"
#ifdef __riscv
#include "copy_space.h"
#else
#include <stdio.h>
static int cs_read(void *p, unsigned n) { return (int)fread(p,1,n,stdin); }
static int cs_write(const void *p, unsigned n) { return (int)fwrite(p,1,n,stdout); }
#endif
#ifdef CS_COPY_PROGRAM
static unsigned char image[262144];
#else
static unsigned char image[65536];
#endif
static char assembly[8192];
#ifdef CS_COPY_OBJECTS
#ifndef CS_COPY_OBJECT_TEXT_BYTES
#define CS_COPY_OBJECT_TEXT_BYTES 32768
#endif
static char object_text[CS_COPY_OBJECT_TEXT_BYTES];
#endif
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
#ifdef CS_COPY_OBJECTS
    struct cs_copy_object objects[8];unsigned count=0,begin=0;
    for (unsigned i=0;i<=size;++i) {
        if (i<size && assembly[i]) continue;
        if (i==begin || count==8) return 2;
        objects[count].assembly=assembly+begin;objects[count++].size=i-begin;
        begin=i+1;
    }
    if (cs_copy_link_objects(image,sizeof(image),CS_COPY_RESULT_ADDRESS_BITS,objects,count,object_text,sizeof(object_text),"value",arguments,2,&error)) return 2;
#elif defined(CS_COPY_PROGRAM)
    if (cs_copy_link_program(image,sizeof(image),CS_COPY_RESULT_ADDRESS_BITS,assembly,size,"value",arguments,2,&error)) return 2;
#else
    if (cs_copy_link_leaf(image,sizeof(image),CS_COPY_RESULT_ADDRESS_BITS,assembly,size,"value",arguments,2,&error)) return 2;
#endif
    unsigned written=0;
    while (written<sizeof(image)) {
        int n=cs_write(image+written,sizeof(image)-written);
        if (n<=0 || (unsigned)n>sizeof(image)-written) return 3;
        written+=(unsigned)n;
    }
    return 0;
}
