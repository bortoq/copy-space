#include "copy_emit.h"
#include <string.h>

static int fits(uint32_t address, uint32_t width, uint32_t limit)
{
    return address <= limit && width <= limit-address;
}

static void field(struct cs_copy_image *image, uint32_t at, unsigned width, uint32_t value)
{
    for (unsigned i=0; i<width; ++i) {
        unsigned char mask=(unsigned char)(1u << (7-((at+i)&7)));
        unsigned char *byte=&image->data[(at+i)/8];
        if ((value>>i)&1) *byte|=mask;
        else *byte&=(unsigned char)~mask;
    }
}

int cs_copy_image_init(struct cs_copy_image *image, unsigned char *data, size_t bytes,
                       unsigned address_bits, uint32_t layer)
{
    if (!image || !data || address_bits<2 || address_bits>31 ||
        bytes>UINT32_MAX/8) return -1;
    unsigned instruction_bits=3*address_bits-1;
    uint32_t layer_bits=256*instruction_bits;
    uint32_t space_bits=UINT32_C(1)<<address_bits;
    if ((layer&7) || bytes*8>space_bits || !fits(layer,layer_bits,(uint32_t)(bytes*8))) return -1;
    *image=(struct cs_copy_image){data,bytes,space_bits,layer,layer_bits,
                                address_bits,address_bits-1,instruction_bits,3};
    memset(data+layer/8,0,layer_bits/8);
    return 0;
}

int cs_copy_constant(struct cs_copy_image *image, uint32_t at, unsigned width, uint32_t value)
{
    if (!image || !width || width>32 ||
        !fits(at,width,(uint32_t)(image->bytes*8))) return -1;
    field(image,at,width,value);
    return 0;
}

int cs_copy_row(struct cs_copy_image *image, unsigned slot, uint32_t count,
                uint32_t destination, uint32_t source)
{
    if (!image || slot>=256 || count>=(UINT32_C(1)<<image->count_bits) ||
        !fits(destination,count,image->space_bits) ||
        !fits(source,count,image->space_bits) || destination>=image->space_bits ||
        source>=image->space_bits) return -1;
    uint32_t at=image->layer+slot*image->instruction_bits;
    field(image,at,image->count_bits,count);
    field(image,at+image->count_bits,image->address_bits,destination);
    field(image,at+image->count_bits+image->address_bits,image->address_bits,source);
    return 0;
}

int cs_copy_emit(struct cs_copy_image *image, uint32_t count, uint32_t destination, uint32_t source)
{
    if (!image || image->slot>=255 || cs_copy_row(image,image->slot,count,destination,source)) return -1;
    ++image->slot;
    return 0;
}

static int overlaps(uint32_t a, unsigned an, uint32_t b, unsigned bn)
{
    return a<b+bn && b<a+an;
}

int cs_copy_add32(struct cs_copy_image *image, uint32_t destination,
                  uint32_t left, uint32_t right, uint32_t table,
                  uint32_t temporary, uint32_t carry)
{
    if (!image || image->address_bits<5 || image->slot>255-193 || (table&15)) return -1;
    uint32_t addresses[]={destination,left,right,table,temporary,carry};
    unsigned widths[]={32,32,32,16,2,1};
    for (unsigned i=0;i<6;++i) {
        if (!fits(addresses[i],widths[i],image->space_bits) ||
            overlaps(addresses[i],widths[i],image->layer,image->layer_bits) ||
            overlaps(addresses[i],widths[i],0,image->layer_bits)) return -1;
        for (unsigned j=0;j<i;++j)
            if ((i>=3 || j>=3) && overlaps(addresses[i],widths[i],addresses[j],widths[j])) return -1;
    }
    for (unsigned i=1;i<3;++i)
        if (destination!=addresses[i] && overlaps(destination,32,addresses[i],32)) return -1;
    if (!fits(table,16,(uint32_t)(image->bytes*8)) ||
        !fits(carry,1,(uint32_t)(image->bytes*8))) return -1;
    for (unsigned i=0;i<8;++i) {
        unsigned sum=(i&1)+((i>>1)&1)+((i>>2)&1);
        field(image,table+2*i,2,sum);
    }
    field(image,carry,1,0);
    /* Each invocation resets carry at execution time as well. */
    cs_copy_emit(image,1,carry,table);
    for (unsigned bit=0;bit<32;++bit) {
        /* Templates execute after being copied into the active layer at 0. */
        uint32_t read=(image->slot+3)*image->instruction_bits;
        uint32_t source_field=read+image->count_bits+image->address_bits;
        cs_copy_emit(image,1,source_field+1,left+bit);
        cs_copy_emit(image,1,source_field+2,right+bit);
        cs_copy_emit(image,1,source_field+3,carry);
        cs_copy_emit(image,2,temporary,table);
        cs_copy_emit(image,1,destination+bit,temporary);
        cs_copy_emit(image,1,carry,temporary+1);
    }
    return 0;
}
