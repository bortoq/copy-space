#include "copy_link.h"
#ifdef __riscv
#include "copy_space.h"
#include <errno.h>
#include <stddef.h>
/* Standalone fixture: newlib's operator buffer uses guest memory. */
static union { long double alignment; unsigned char bytes[131072]; } heap;
static size_t heap_used;
void *_sbrk(ptrdiff_t increment)
{
    size_t next;
    if (increment>=0) {
        if ((size_t)increment>sizeof(heap.bytes)-heap_used) { errno=ENOMEM;return (void *)-1; }
        next=heap_used+(size_t)increment;
    } else {
        size_t decrease=(size_t)(-(increment+1))+1;
        if (decrease>heap_used) { errno=ENOMEM;return (void *)-1; }
        next=heap_used-decrease;
    }
    void *previous=heap.bytes+heap_used;
    heap_used=next;
    return previous;
}
#else
#include <stdio.h>
static int cs_read(void *p, unsigned n) { return (int)fread(p,1,n,stdin); }
static int cs_write(const void *p, unsigned n) { return (int)fwrite(p,1,n,stdout); }
#endif
#ifdef CS_COPY_PROGRAM
#ifndef CS_COPY_IMAGE_BYTES
#define CS_COPY_IMAGE_BYTES 262144
#endif
#else
#ifndef CS_COPY_IMAGE_BYTES
#define CS_COPY_IMAGE_BYTES 65536
#endif
#endif
static unsigned char image[CS_COPY_IMAGE_BYTES];
#ifndef CS_COPY_ASSEMBLY_BYTES
#define CS_COPY_ASSEMBLY_BYTES 8192
#endif
static char assembly[CS_COPY_ASSEMBLY_BYTES];
#if defined(CS_COPY_OBJECTS) && !defined(CS_COPY_OBJECT_ALLOC)
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
#ifdef CS_COPY_ARCHIVE
    if (size<4) return 2;
    uint32_t object_size=0;
    for (unsigned i=0;i<4;++i) object_size|=(uint32_t)(unsigned char)assembly[i]<<(8*i);
    if (object_size>size-4) return 2;
    const struct cs_copy_object object={assembly+4,object_size};
    if (cs_copy_link_archive_alloc(image,sizeof(image),CS_COPY_RESULT_ADDRESS_BITS,8192,
        &object,1,assembly+4+object_size,size-4-object_size,"value",arguments,2,&error)) {
#ifndef __riscv
        fprintf(stderr,"%zu: %s\n",error.line,error.message);
#endif
        return 2;
    }
#elif defined(CS_COPY_OBJECTS)
    struct cs_copy_object objects[8];unsigned count=0,begin=0;
    for (unsigned i=0;i<=size;++i) {
        if (i<size && assembly[i]) continue;
        if (i==begin || count==8) return 2;
        objects[count].assembly=assembly+begin;objects[count++].size=i-begin;
        begin=i+1;
    }
    if (
#ifdef CS_COPY_OBJECT_ALLOC
        cs_copy_link_objects_alloc(image,sizeof(image),CS_COPY_RESULT_ADDRESS_BITS,
#ifdef CS_COPY_MEMORY_BYTES
        CS_COPY_MEMORY_BYTES,
#else
        8192,
#endif
        objects,count,"value",arguments,2,&error)
#else
#ifdef CS_COPY_MEMORY_BYTES
        cs_copy_link_objects_memory(image,sizeof(image),CS_COPY_RESULT_ADDRESS_BITS,CS_COPY_MEMORY_BYTES,
#else
        cs_copy_link_objects(image,sizeof(image),CS_COPY_RESULT_ADDRESS_BITS,
#endif
        objects,count,object_text,sizeof(object_text),"value",arguments,2,&error)
#endif
        ) {
#ifndef __riscv
        fprintf(stderr,"%zu: %s\n",error.line,error.message);
#endif
        return 2;
    }
#elif defined(CS_COPY_PROGRAM)
    if (
#ifdef CS_COPY_MEMORY_BYTES
        cs_copy_link_program_memory(image,sizeof(image),CS_COPY_RESULT_ADDRESS_BITS,CS_COPY_MEMORY_BYTES,
#else
        cs_copy_link_program(image,sizeof(image),CS_COPY_RESULT_ADDRESS_BITS,
#endif
        assembly,size,"value",arguments,2,&error)) {
#ifndef __riscv
        fprintf(stderr,"%zu: %s\n",error.line,error.message);
#endif
        return 2;
    }
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
