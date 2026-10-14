#include "copy_emit.h"
#ifdef __riscv
#include "copy_space.h"
#else
#include <stdio.h>
static int cs_read(void *p, unsigned n) { return (int)fread(p,1,n,stdin); }
static int cs_write(const void *p, unsigned n) { return (int)fwrite(p,1,n,stdout); }
#endif
static unsigned char data[32768];
#ifndef CS_COPY_CHAIN_OPERATION
#define CS_COPY_CHAIN_OPERATION 0
#endif
#ifndef CS_COPY_ADDRESS_BITS
#define CS_COPY_ADDRESS_BITS 24
#endif
#define LAYER_BITS (256*(3*CS_COPY_ADDRESS_BITS-1))
#if CS_COPY_CHAIN_OPERATION < 2
#define CODE_LIMIT (65536+3*LAYER_BITS)
#define SECOND_LAYER (65536+LAYER_BITS)
#define OUTPUT_LAYER (65536+2*LAYER_BITS)
#else
#define CODE_LIMIT (65536+2*LAYER_BITS)
#define SECOND_LAYER 65536
#define OUTPUT_LAYER (65536+LAYER_BITS)
#endif
static int operation(struct cs_copy_program *program, uint32_t destination, uint32_t left, uint32_t right)
{
#if CS_COPY_CHAIN_OPERATION == 0
    return cs_copy_program_add32(program,destination,left,right,33024,32900,32902);
#elif CS_COPY_CHAIN_OPERATION == 1
    return cs_copy_program_sub32(program,destination,left,right,33024,32900,32902);
#else
    return cs_copy_program_bits32(program,(enum cs_copy_bit_operation)(CS_COPY_CHAIN_OPERATION-2),destination,left,right,33024);
#endif
}
int main(void)
{
    unsigned char input[12];
    unsigned read=0;
    while (read<sizeof(input)) {
        int n=cs_read(input+read,sizeof(input)-read);
        if (n<=0 || (unsigned)n>sizeof(input)-read) return 1;
        read+=(unsigned)n;
    }
    struct cs_copy_program program;
    if (!cs_copy_program_init(&program,data,sizeof(data),CS_COPY_ADDRESS_BITS,0,CODE_LIMIT)) return 2;
    if (cs_copy_program_init(&program,data,sizeof(data),CS_COPY_ADDRESS_BITS,65536,CODE_LIMIT)) return 2;
    for (unsigned i=0;i<3;++i) {
        uint32_t value=0;
        for (unsigned j=0;j<4;++j) value|=(uint32_t)input[4*i+j]<<(8*j);
        if (cs_copy_constant(&program.image,32768+32*i,32,value)) return 3;
    }
    if (!cs_copy_program_add32(&program,65536,32768,32800,33024,32900,32902) ||
        !cs_copy_program_bits32(&program,(enum cs_copy_bit_operation)99,32864,32768,32800,33024) ||
        program.image.slot!=3 || program.code_end!=65536+LAYER_BITS) return 4;
    if (operation(&program,32864,32768,32800) || operation(&program,32864,32864,32832)) return 5;
    if (program.image.layer!=SECOND_LAYER) return 6;
    for (unsigned i=0;i<32;++i)
        if (cs_copy_program_emit(&program,1,34000+(i/8)*8+7-(i%8),32864+i)) return 7;
    if (cs_copy_program_next(&program) ||
        cs_copy_row(&program.image,2,32,34000,34100)) return 8;
    if (!cs_copy_program_next(&program) || program.image.layer!=OUTPUT_LAYER ||
        program.code_end!=CODE_LIMIT) return 9;
    data[36352/8]=1;
    if (!cs_copy_program_finish(&program,36352)) return 10;
    data[36352/8]=0;
    if (cs_copy_program_finish(&program,36352)) return 11;
    unsigned written=0;
    while (written<sizeof(data)) {
        int n=cs_write(data+written,sizeof(data)-written);
        if (n<=0 || (unsigned)n>sizeof(data)-written) return 12;
        written+=(unsigned)n;
    }
    return 0;
}
