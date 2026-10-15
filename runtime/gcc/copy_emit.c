#include "copy_emit.h"
#include <string.h>

static int fits(uint32_t address, uint32_t width, uint32_t limit)
{
    return address <= limit && width <= limit-address;
}

static const unsigned char reverse_byte[256]={
    0,128,64,192,32,160,96,224,16,144,80,208,48,176,112,240,
    8,136,72,200,40,168,104,232,24,152,88,216,56,184,120,248,
    4,132,68,196,36,164,100,228,20,148,84,212,52,180,116,244,
    12,140,76,204,44,172,108,236,28,156,92,220,60,188,124,252,
    2,130,66,194,34,162,98,226,18,146,82,210,50,178,114,242,
    10,138,74,202,42,170,106,234,26,154,90,218,58,186,122,250,
    6,134,70,198,38,166,102,230,22,150,86,214,54,182,118,246,
    14,142,78,206,46,174,110,238,30,158,94,222,62,190,126,254,
    1,129,65,193,33,161,97,225,17,145,81,209,49,177,113,241,
    9,137,73,201,41,169,105,233,25,153,89,217,57,185,121,249,
    5,133,69,197,37,165,101,229,21,149,85,213,53,181,117,245,
    13,141,77,205,45,173,109,237,29,157,93,221,61,189,125,253,
    3,131,67,195,35,163,99,227,19,147,83,211,51,179,115,243,
    11,139,75,203,43,171,107,235,27,155,91,219,59,187,123,251,
    7,135,71,199,39,167,103,231,23,151,87,215,55,183,119,247,
    15,143,79,207,47,175,111,239,31,159,95,223,63,191,127,255,
};

static void field(struct cs_copy_image *image, uint32_t at, unsigned width, uint32_t value)
{
    if (width==1) {
        unsigned char mask=(unsigned char)(1u<<(7-(at&7)));
        unsigned char *byte=&image->data[at/8];
        *byte=(unsigned char)((*byte&~mask) | ((value&1) ? mask : 0));
        return;
    }
    while (width) {
        unsigned offset=at&7, count=8-offset;
        if (count>width) count=width;
        unsigned mask=(255u>>offset)&(255u<<(8-offset-count));
        unsigned char *byte=&image->data[at/8];
        *byte=(unsigned char)((*byte&~mask) | ((reverse_byte[value&255]>>offset)&mask));
        value>>=count;at+=count;width-=count;
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

static int row_valid(const struct cs_copy_image *image, unsigned slot, uint32_t count,
                     uint32_t destination, uint32_t source)
{
    if (!image || slot>=256 || count>=(UINT32_C(1)<<image->count_bits) ||
        !fits(destination,count,image->space_bits) ||
        !fits(source,count,image->space_bits) || destination>=image->space_bits ||
        source>=image->space_bits) return 0;
    return 1;
}

int cs_copy_row(struct cs_copy_image *image, unsigned slot, uint32_t count,
                uint32_t destination, uint32_t source)
{
    if (!row_valid(image,slot,count,destination,source)) return -1;
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

static int add_valid(const struct cs_copy_image *image, uint32_t destination,
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
    return 0;
}

static int arithmetic32(struct cs_copy_image *image, int subtract, uint32_t destination,
                  uint32_t left, uint32_t right, uint32_t table,
                  uint32_t temporary, uint32_t carry)
{
    if (add_valid(image,destination,left,right,table,temporary,carry)) return -1;
    for (unsigned i=0;i<8;++i) {
        unsigned a=i&1,b=(i>>1)&1,c=(i>>2)&1;
        unsigned value=subtract ? (((a-b-c)&1)|((unsigned)(a<b+c)<<1)) : a+b+c;
        field(image,table+2*i,2,value);
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

int cs_copy_add32(struct cs_copy_image *image, uint32_t destination,
                  uint32_t left, uint32_t right, uint32_t table,
                  uint32_t temporary, uint32_t carry)
{
    return arithmetic32(image,0,destination,left,right,table,temporary,carry);
}

int cs_copy_sub32(struct cs_copy_image *image, uint32_t destination,
                  uint32_t left, uint32_t right, uint32_t table,
                  uint32_t temporary, uint32_t borrow)
{
    return arithmetic32(image,1,destination,left,right,table,temporary,borrow);
}

static int bits_valid(const struct cs_copy_image *image, enum cs_copy_bit_operation operation,
                      uint32_t destination, uint32_t left, uint32_t right, uint32_t table)
{
    if (!image || (unsigned)operation>CS_COPY_XOR || image->slot>255-96 || (table&3) ||
        !fits(table,4,(uint32_t)(image->bytes*8))) return -1;
    uint32_t addresses[]={destination,left,right,table};
    unsigned widths[]={32,32,32,4};
    for (unsigned i=0;i<4;++i) {
        if (!fits(addresses[i],widths[i],image->space_bits) ||
            overlaps(addresses[i],widths[i],0,image->layer_bits) ||
            overlaps(addresses[i],widths[i],image->layer,image->layer_bits)) return -1;
        if (i<3 && overlaps(addresses[i],32,table,4)) return -1;
    }
    for (unsigned i=1;i<3;++i)
        if (destination!=addresses[i] && overlaps(destination,32,addresses[i],32)) return -1;
    return 0;
}

int cs_copy_bits32(struct cs_copy_image *image, enum cs_copy_bit_operation operation,
                   uint32_t destination, uint32_t left, uint32_t right, uint32_t table)
{
    if (bits_valid(image,operation,destination,left,right,table)) return -1;
    const unsigned truth[]={8,14,6};
    field(image,table,4,truth[operation]);
    for (unsigned bit=0;bit<32;++bit) {
        uint32_t source_field=(image->slot+2)*image->instruction_bits+image->count_bits+image->address_bits;
        cs_copy_emit(image,1,source_field,left+bit);
        cs_copy_emit(image,1,source_field+1,right+bit);
        cs_copy_emit(image,1,destination+bit,table);
    }
    return 0;
}

int cs_copy_program_init(struct cs_copy_program *program, unsigned char *data, size_t bytes,
                         unsigned address_bits, uint32_t code_begin, uint32_t code_limit)
{
    if (!program || address_bits<2 || address_bits>31 || bytes>UINT32_MAX/8) return -1;
    uint32_t layer_bits=256*(3*address_bits-1);
    if (code_begin<layer_bits || code_limit>bytes*8 || code_begin>code_limit ||
        !fits(code_begin,layer_bits,code_limit) || layer_bits>=(UINT32_C(1)<<(address_bits-1))) return -1;
    struct cs_copy_image image;
    if (cs_copy_image_init(&image,data,bytes,address_bits,code_begin)) return -1;
    *program=(struct cs_copy_program){image,code_begin,code_begin+layer_bits,code_limit};
    return 0;
}

int cs_copy_program_next(struct cs_copy_program *program)
{
    if (!program || !fits(program->code_end,program->image.layer_bits,program->code_limit) ||
        !row_valid(&program->image,255,program->image.layer_bits,0,program->code_end)) return -1;
    struct cs_copy_image next;
    if (cs_copy_image_init(&next,program->image.data,program->image.bytes,
                          program->image.address_bits,program->code_end)) return -1;
    cs_copy_row(&program->image,255,program->image.layer_bits,0,program->code_end);
    program->image=next;
    program->code_end+=next.layer_bits;
    return 0;
}

static int room(struct cs_copy_program *program, unsigned count)
{
    if (!program || count>252) return -1;
    if (program->image.slot<=255-count) return 0;
    return cs_copy_program_next(program);
}

int cs_copy_program_patch_jump(struct cs_copy_program *program, uint32_t layer, uint32_t target)
{
    if (!program || layer<program->code_begin || target<program->code_begin ||
        layer>=program->code_end || target>=program->code_end ||
        (layer-program->code_begin)%program->image.layer_bits ||
        (target-program->code_begin)%program->image.layer_bits) return -1;
    struct cs_copy_image from=program->image;
    from.layer=layer;
    return cs_copy_row(&from,255,from.layer_bits,0,target);
}

int cs_copy_program_emit(struct cs_copy_program *program, uint32_t count,
                         uint32_t destination, uint32_t source)
{
    if (!program || !row_valid(&program->image,3,count,destination,source) || room(program,1)) return -1;
    return cs_copy_emit(&program->image,count,destination,source);
}

static int program_arithmetic32(struct cs_copy_program *program, int subtract, uint32_t destination,
                          uint32_t left, uint32_t right, uint32_t table,
                          uint32_t temporary, uint32_t carry)
{
    if (!program) return -1;
    uint32_t addresses[]={destination,left,right,table,temporary,carry};
    unsigned widths[]={32,32,32,16,2,1};
    for (unsigned i=0;i<6;++i)
        if (overlaps(addresses[i],widths[i],program->code_begin,program->code_limit-program->code_begin)) return -1;
    struct cs_copy_image probe=program->image;
    probe.slot=3;
    if (add_valid(&probe,destination,left,right,table,temporary,carry) || room(program,193)) return -1;
    return arithmetic32(&program->image,subtract,destination,left,right,table,temporary,carry);
}

int cs_copy_program_add32(struct cs_copy_program *program, uint32_t destination,
                          uint32_t left, uint32_t right, uint32_t table,
                          uint32_t temporary, uint32_t carry)
{
    return program_arithmetic32(program,0,destination,left,right,table,temporary,carry);
}

int cs_copy_program_sub32(struct cs_copy_program *program, uint32_t destination,
                          uint32_t left, uint32_t right, uint32_t table,
                          uint32_t temporary, uint32_t borrow)
{
    return program_arithmetic32(program,1,destination,left,right,table,temporary,borrow);
}

int cs_copy_program_bits32(struct cs_copy_program *program, enum cs_copy_bit_operation operation,
                           uint32_t destination, uint32_t left, uint32_t right, uint32_t table)
{
    if (!program) return -1;
    uint32_t addresses[]={destination,left,right,table};
    unsigned widths[]={32,32,32,4};
    for (unsigned i=0;i<4;++i)
        if (overlaps(addresses[i],widths[i],program->code_begin,program->code_limit-program->code_begin)) return -1;
    struct cs_copy_image probe=program->image;
    probe.slot=3;
    if (bits_valid(&probe,operation,destination,left,right,table) || room(program,96)) return -1;
    return cs_copy_bits32(&program->image,operation,destination,left,right,table);
}

int cs_copy_program_finish(struct cs_copy_program *program, uint32_t zero_layer)
{
    if (!program || (zero_layer&7) ||
        !fits(zero_layer,program->image.layer_bits,(uint32_t)(program->image.bytes*8)) ||
        overlaps(zero_layer,program->image.layer_bits,0,program->image.layer_bits) ||
        overlaps(zero_layer,program->image.layer_bits,program->code_begin,program->code_limit-program->code_begin)) return -1;
    for (unsigned i=0;i<program->image.layer_bits/8;++i)
        if (program->image.data[zero_layer/8+i]) return -1;
    struct cs_copy_image boot;
    if (cs_copy_image_init(&boot,program->image.data,program->image.bytes,program->image.address_bits,0)) return -1;
    cs_copy_row(&program->image,255,program->image.layer_bits,0,zero_layer);
    return cs_copy_row(&boot,255,boot.layer_bits,0,program->code_begin);
}
