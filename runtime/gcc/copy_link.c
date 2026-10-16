#include "copy_link.h"
#include "copy_emit.h"
#include <string.h>
#include <stdlib.h>
#include <limits.h>

/* These limits also determine the physical tables before generated code. */
#ifndef CS_COPY_LABEL_CAPACITY
#define CS_COPY_LABEL_CAPACITY 32
#endif
#ifndef CS_COPY_JUMP_CAPACITY
#define CS_COPY_JUMP_CAPACITY 64
#endif
#ifndef CS_COPY_CALL_CAPACITY
#define CS_COPY_CALL_CAPACITY 32
#endif
#ifndef CS_COPY_SYMBOL_CAPACITY
#define CS_COPY_SYMBOL_CAPACITY 12
#endif
#ifndef CS_COPY_RELOCATION_CAPACITY
#define CS_COPY_RELOCATION_CAPACITY 64
#endif
#if CS_COPY_LABEL_CAPACITY < 1 || CS_COPY_LABEL_CAPACITY > 1048576 || \
    CS_COPY_JUMP_CAPACITY < 1 || CS_COPY_JUMP_CAPACITY > 1048576 || \
    CS_COPY_CALL_CAPACITY < 1 || CS_COPY_CALL_CAPACITY > 1048576 || \
    CS_COPY_SYMBOL_CAPACITY < 1 || CS_COPY_SYMBOL_CAPACITY > 1048576 || \
    CS_COPY_RELOCATION_CAPACITY < 1 || CS_COPY_RELOCATION_CAPACITY > 1048576
#error "copy table capacities must be in 1..1048576"
#endif

enum { REG_BASE=32768, CONSTANT_BASE=24576,
       CONSTANT_CAPACITY=(REG_BASE-CONSTANT_BASE)/32, ADD_TABLE=33792,
       SUB_TABLE=33808, AND_TABLE=33824, OR_TABLE=33828, XOR_TABLE=33832,
       TEMPORARY=33840, CARRY=33842, SHIFT_WORD=33856, SHIFT_COUNT=33888,
       SHIFT_PAIR=33894, SHIFT_ZERO=33896,
       CMP_EQ=33900, CMP_LTU=33901, CMP_LTS=33902, CMP_LEU=33903,
       CMP_LES=33904, CMP_SIGN=33905, EQ_TABLE=33920, LT_TABLE=33928,
       BRANCH_TABLE=60032,
       MUL_LEFT=34240, MUL_RIGHT=34272, MUL_ACC=34304,
       MUL_ADDEND=34336, MUL_MARKER=34368, MUL_STOP=34400,
       DIV_NUM=34528, DIV_DEN=34560, DIV_REM=34592, DIV_QUO=34624,
       DIV_MARK=34656, DIV_OVERFLOW=34688, DIV_STOP=34689,
       DIV_FLAGS=34690, DIV_REDUCE=34695, DIV_NUM_SIGN=34696,
       DIV_DEN_SIGN=34697, DIV_SIGN=34698,
       MEM_ADDRESS=34720, MEM_FLAGS=34752, MEM_VALID=34757, MEM_BIT_ADDRESS=34784,
       STACK_VALUE=34816,
       RETURN_FP=34848, RETURN_PC=34880, CALL_TARGET=34912,
       CALL_TABLE=BRANCH_TABLE+64*CS_COPY_JUMP_CAPACITY,
       SYMBOL_TABLE=CALL_TABLE+32*CS_COPY_CALL_CAPACITY,
       CODE_BEGIN=SYMBOL_TABLE+32*CS_COPY_SYMBOL_CAPACITY,
       OUTPUT=34000, STATUS=34100, ZERO_LAYER=36352 };
struct data_section { char name[64]; uint32_t position,alignment,base; int kind; };
struct data_fragment { uint32_t staging,offset,count; unsigned section; };
struct context {
    struct cs_copy_program program;
    uint32_t constants[CONSTANT_CAPACITY];
    unsigned constant_count;
    struct { char name[64]; uint32_t address; int defined, data, alias, weak, missing_weak, numbered; size_t offset; } labels[CS_COPY_LABEL_CAPACITY];
    struct { uint32_t layer, table, fallthrough; int label, inverted; size_t line; } jumps[CS_COPY_JUMP_CAPACITY];
    unsigned label_count, jump_count;
    int compared;
    uint32_t data_begin;
    uint32_t memory_bytes;
    unsigned memory_address_bits;
    int memory_fault;
    int return_handler;
    unsigned call_count;
    struct { int label; uint32_t addend; } symbols[CS_COPY_SYMBOL_CAPACITY];
    unsigned symbol_count;
    int program_mode;
    int section;
    struct data_section *sections;
    unsigned section_count,section_capacity,active_section,previous_section;
    int previous_valid;
    unsigned section_stack[16],section_depth;
    struct data_fragment *fragments;
    unsigned fragment_count,fragment_capacity;
    uint32_t data_cursor;
    struct { uint64_t addend; uint32_t destination; int label,subtract; unsigned bytes; } relocations[CS_COPY_RELOCATION_CAPACITY];
    unsigned relocation_count;
    struct { int label,target; uint32_t addend; } aliases[CS_COPY_LABEL_CAPACITY];
    unsigned alias_count;
    const char *assembly;
    size_t assembly_size,statement_offset;
};

static size_t statement_end(const char *, size_t, size_t, size_t *);
static int decimal_label_range(const char *s, const char *limit, const char **end, uint32_t *number)
{
    uint32_t n=0;
    if (s==limit || *s<'0' || *s>'9') return -1;
    do {
        unsigned digit=(unsigned)(*s++-'0');
        if (n>(UINT32_MAX-digit)/10) return -1;
        n=n*10+digit;
    } while (s!=limit && *s>='0' && *s<='9');
    *end=s;*number=n;return 0;
}
static int decimal_label(const char *s, const char **end, uint32_t *number)
{
    return decimal_label_range(s,NULL,end,number);
}
static int numeric_target(const char *assembly, size_t size, size_t before,
                          uint32_t number, int forward, size_t *target)
{
    int found=0;
    size_t offset=0;
    while (offset<size) {
        size_t next,end=statement_end(assembly,size,offset,&next),start=offset;
        while (start<end && (assembly[start]==' ' || assembly[start]=='\t' || assembly[start]=='\r')) ++start;
        const char *after;uint32_t value;
        if (start<end && !decimal_label_range(assembly+start,assembly+end,&after,&value)) {
            while (after<assembly+end && (*after==' ' || *after=='\t' || *after=='\r')) ++after;
            if (after<assembly+end && *after==':' && value==number &&
                ((forward && offset>before) || (!forward && offset<before))) {
                *target=offset;found=1;
                if (forward) return 0;
            }
        }
        offset=next;
    }
    return found ? 0 : -1;
}
static int numeric_label(struct context *ctx, size_t offset)
{
    for (unsigned i=0;i<ctx->label_count;++i)
        if (ctx->labels[i].numbered && ctx->labels[i].offset==offset) return (int)i;
    if (ctx->label_count==CS_COPY_LABEL_CAPACITY) return -1;
    unsigned i=ctx->label_count++;
    ctx->labels[i].numbered=1;ctx->labels[i].offset=offset;
    return (int)i;
}

static int label(struct context *ctx, const char *name)
{
    size_t length=strlen(name);
    const char *end;uint32_t number;
    if (!decimal_label(name,&end,&number) && (*end=='b' || *end=='f') && !end[1]) {
        size_t target;
        if (ctx->statement_offset==SIZE_MAX || numeric_target(ctx->assembly,ctx->assembly_size,
            ctx->statement_offset,number,*end=='f',&target)) return -1;
        return numeric_label(ctx,target);
    }
    if (!length || length>=sizeof(ctx->labels[0].name)) return -1;
    for (size_t i=0;i<length;++i) {
        unsigned char c=(unsigned char)name[i];
        if (!(c=='_' || c=='.' || c=='$' || (c>='a' && c<='z') ||
              (c>='A' && c<='Z') || (i && c>='0' && c<='9'))) return -1;
    }
    for (unsigned i=0;i<ctx->label_count;++i)
        if (!strcmp(ctx->labels[i].name,name)) return (int)i;
    if (ctx->label_count==CS_COPY_LABEL_CAPACITY) return -1;
    unsigned i=ctx->label_count++;
    memcpy(ctx->labels[i].name,name,length+1);
    return (int)i;
}

static int jump(struct context *ctx, int target, size_t line)
{
    if (ctx->jump_count==CS_COPY_JUMP_CAPACITY) return -1;
    unsigned i=ctx->jump_count;
    uint32_t layer=ctx->program.image.layer;
    if (cs_copy_program_next(&ctx->program)) return -1;
    ctx->jumps[i].layer=layer; ctx->jumps[i].label=target; ctx->jumps[i].line=line;
    ++ctx->jump_count;
    return 0;
}

static int whitespace(unsigned char c) { return c==' ' || c=='\t' || c=='\r'; }
static char *trim(char *s)
{
    while (whitespace((unsigned char)*s)) ++s;
    size_t n=strlen(s);
    while (n && whitespace((unsigned char)s[n-1])) s[--n]=0;
    return s;
}
static int reg(const char *s, uint32_t *address)
{
    if (!strcmp(s,"$fp")) { *address=REG_BASE; return 0; }
    if (!strcmp(s,"$sp")) { *address=REG_BASE+32; return 0; }
    if (s[0]!='$' || s[1]!='r') return -1;
    unsigned n=0, digits=0;
    for (s+=2; *s; ++s) {
        if (*s<'0' || *s>'9' || ++digits>2) return -1;
        n=n*10+(unsigned)(*s-'0');
    }
    if (!digits || n>13) return -1;
    *address=REG_BASE+32*(n+2);
    return 0;
}
static int integer(const char *s, uint32_t *value)
{
    unsigned negative=0, signs=0;
    while (*s=='+' || *s=='-') {
        if (++signs>2) return -1;
        negative^=(*s++=='-');
    }
    unsigned base=10;
    if (s[0]=='0' && (s[1]=='x' || s[1]=='X')) { base=16; s+=2; }
    else if (s[0]=='0' && s[1]) base=8;
    if (!*s) return -1;
    uint32_t n=0;
    for (;*s;++s) {
        unsigned d;
        if (*s>='0' && *s<='9') d=(unsigned)(*s-'0');
        else if (*s>='a' && *s<='f') d=(unsigned)(*s-'a'+10);
        else if (*s>='A' && *s<='F') d=(unsigned)(*s-'A'+10);
        else return -1;
        if (d>=base || n>(UINT32_MAX-d)/base) return -1;
        n=n*base+d;
    }
    if (negative && n>UINT32_C(0x80000000)) return -1;
    *value=negative ? 0-n : n;
    return 0;
}
static int constant(struct context *ctx, uint32_t value, uint32_t *address)
{
    unsigned i;
    for (i=0;i<ctx->constant_count;++i) if (ctx->constants[i]==value) break;
    if (i==ctx->constant_count) {
        if (i==CONSTANT_CAPACITY) return -1;
        ctx->constants[i]=value;
        ++ctx->constant_count;
        if (cs_copy_constant(&ctx->program.image,CONSTANT_BASE+32*i,32,value)) return -1;
    }
    *address=CONSTANT_BASE+32*i;
    return 0;
}
static int expression(struct context *ctx, const char *text, int *index, uint32_t *addend)
{
    char name[64];
    size_t n=0;
    while (text[n] && text[n]!='+' && text[n]!='-') ++n;
    if (!n || n>=sizeof(name)) return -1;
    memcpy(name,text,n);name[n]=0;
    *index=label(ctx,trim(name));*addend=0;
    if (*index<0) return -1;
    if (text[n]) {
        uint32_t value;
        const char *number=text+n+1;
        while (whitespace((unsigned char)*number)) ++number;
        if (integer(number,&value)) return -1;
        *addend=text[n]=='-' ? 0-value : value;
    }
    return 0;
}
static int hex_digit(unsigned char c)
{
    if (c>='0' && c<='9') return c-'0';
    if (c>='a' && c<='f') return c-'a'+10;
    if (c>='A' && c<='F') return c-'A'+10;
    return -1;
}
static int integer64(const char *s, uint64_t *value)
{
    unsigned negative=0,signs=0,base=10;
    while (*s=='+' || *s=='-') {
        if (++signs>2) return -1;
        negative^=(*s++=='-');
    }
    if (s[0]=='0' && (s[1]=='x' || s[1]=='X')) { base=16;s+=2; }
    else if (s[0]=='0' && s[1]) base=8;
    if (!*s) return -1;
    uint64_t n=0;
    for (;*s;++s) {
        int d=hex_digit((unsigned char)*s);
        if (d<0 || (unsigned)d>=base || n>(UINT64_MAX-(unsigned)d)/base) return -1;
        n=n*base+(unsigned)d;
    }
    if (negative && n>(UINT64_C(1)<<63)) return -1;
    *value=negative ? 0-n : n;
    return 0;
}
static int data_symbol(struct context *ctx, const char **text, int *index)
{
    const char *at=*text;
    unsigned parentheses=0;
    while (whitespace((unsigned char)*at)) ++at;
    while (*at=='(') {
        if (++parentheses>32) return -1;
        ++at;
        while (whitespace((unsigned char)*at)) ++at;
    }
    char name[64];size_t n=0;
    while (at[n] && !whitespace((unsigned char)at[n]) &&
           at[n]!='+' && at[n]!='-' && at[n]!='(' && at[n]!=')') ++n;
    if (!n || n>=sizeof(name)) return -1;
    memcpy(name,at,n);name[n]=0;
    *index=label(ctx,name);
    if (*index<0) return -1;
    at+=n;
    while (whitespace((unsigned char)*at)) ++at;
    while (parentheses) {
        if (*at++!=')') return -1;
        --parentheses;
        while (whitespace((unsigned char)*at)) ++at;
    }
    *text=at;return 0;
}
static int data_expression(struct context *ctx, const char *text, int *index,
                           int *subtract, uint64_t *addend)
{
    /* Preserve existing symbol+32-bit-addend initializers. Relative label
     * tables need both labels resolved after code/data placement. */
    uint32_t offset;
    *subtract=-1;
    if (!expression(ctx,text,index,&offset)) { *addend=offset;return 0; }
    if (data_symbol(ctx,&text,index) || *text++!='-' ||
        data_symbol(ctx,&text,subtract)) return -1;
    *addend=0;
    if (*text) {
        char sign=*text++;
        if (sign!='+' && sign!='-') return -1;
        while (whitespace((unsigned char)*text)) ++text;
        uint64_t value;
        if (integer64(text,&value)) return -1;
        *addend=sign=='-' ? 0-value : value;
    }
    return 0;
}
/* Keep indices stable while the arrays grow. Allocate before replacing the
 * old table so all failure paths can release the current allocation. */
static void *grow_table(void *table, unsigned *capacity, size_t item_bytes)
{
    if (*capacity>UINT_MAX/2) return NULL;
    unsigned next=*capacity ? *capacity*2 : 16;
    if (item_bytes>SIZE_MAX/next) return NULL;
    void *larger=malloc(next*item_bytes);
    if (!larger) return NULL;
    if (*capacity) memcpy(larger,table,*capacity*item_bytes);
    free(table);
    *capacity=next;
    return larger;
}
static int data_reserve(struct context *ctx, uint32_t count, uint32_t *at)
{
    uint32_t capacity=ctx->memory_bytes/2;
    if (ctx->data_cursor>capacity || count>capacity-ctx->data_cursor) return -1;
    *at=ctx->data_begin+ctx->data_cursor*8;
    if (count) {
        unsigned index=ctx->fragment_count;
        uint32_t offset=ctx->sections[ctx->active_section].position;
        if (index && ctx->fragments[index-1].section==ctx->active_section &&
            ctx->fragments[index-1].staging+ctx->fragments[index-1].count==ctx->data_cursor &&
            ctx->fragments[index-1].offset+ctx->fragments[index-1].count==offset) {
            ctx->fragments[index-1].count+=count;
        } else {
            if (index==ctx->fragment_capacity) {
                void *larger=grow_table(ctx->fragments,&ctx->fragment_capacity,sizeof(*ctx->fragments));
                if (!larger) return -1;
                ctx->fragments=larger;
            }
            ctx->fragments[index].staging=ctx->data_cursor;
            ctx->fragments[index].offset=offset;
            ctx->fragments[index].count=count;
            ctx->fragments[index].section=ctx->active_section;
            ++ctx->fragment_count;
        }
    }
    ctx->sections[ctx->active_section].position+=count;
    ctx->data_cursor+=count;
    return 0;
}
static int data_align(struct context *ctx, uint32_t alignment)
{
    if (!alignment || alignment>ctx->memory_bytes/2 || (alignment&(alignment-1))) return -1;
    if (alignment>ctx->sections[ctx->active_section].alignment) ctx->sections[ctx->active_section].alignment=alignment;
    uint32_t padding=(0-ctx->sections[ctx->active_section].position)&(alignment-1),at;
    return data_reserve(ctx,padding,&at);
}
static int select_section(struct context *ctx, const char *name, int kind)
{
    int previous_valid=ctx->section_count!=0;
    unsigned i;
    for (i=0;i<ctx->section_count;++i) if (!strcmp(ctx->sections[i].name,name)) break;
    if (i==ctx->section_count) {
        size_t length=strlen(name);
        /* Label.data stores section index + 1 in an int. */
        if (i>=INT_MAX || length>=sizeof(ctx->sections[i].name)) return -1;
        if (i==ctx->section_capacity) {
            void *larger=grow_table(ctx->sections,&ctx->section_capacity,sizeof(*ctx->sections));
            if (!larger) return -1;
            ctx->sections=larger;
        }
        memset(&ctx->sections[i],0,sizeof(ctx->sections[i]));
        memcpy(ctx->sections[i].name,name,length+1);
        ctx->sections[i].kind=kind;ctx->sections[i].alignment=1;++ctx->section_count;
    } else if (ctx->sections[i].kind!=kind) return -1;
    ctx->previous_section=ctx->active_section;
    ctx->previous_valid=previous_valid;
    ctx->active_section=i;ctx->section=kind;
    return 0;
}
static int section_directive(struct context *ctx, const char *arguments)
{
    char name[64];size_t n=0;const char *p=arguments;
    if (*p=='"') ++p;
    while (*p && *p!=',' && *p!='"' && !whitespace((unsigned char)*p)) {
        if (n+1==sizeof(name)) return -1;
        name[n++]=*p++;
    }
    name[n]=0;
    if (!n) return -1;
    int kind=-1;
    if (!strcmp(name,".text") || !strncmp(name,".text.",6)) kind=0;
    else if (!strcmp(name,".data") || !strncmp(name,".data.",6) ||
             !strcmp(name,".rodata") || !strncmp(name,".rodata.",8) ||
             !strcmp(name,".sdata") || !strncmp(name,".sdata.",7)) kind=1;
    else if (!strcmp(name,".bss") || !strncmp(name,".bss.",5) ||
             !strcmp(name,".sbss") || !strncmp(name,".sbss.",7)) kind=2;
    else if (!strcmp(name,".note.GNU-stack")) kind=3;
    else {
        if (*p=='"') ++p;
        while (whitespace((unsigned char)*p)) ++p;
        if (!*p) {
            for (unsigned i=0;i<ctx->section_count;++i)
                if (!strcmp(ctx->sections[i].name,name)) return select_section(ctx,name,ctx->sections[i].kind);
            return -1;
        }
        if (*p++!=',') return -1;
        while (whitespace((unsigned char)*p)) ++p;
        if (*p++!='"') return -1;
        int alloc=0,execute=0;
        while (*p && *p!='"') {
            if (*p=='a') alloc=1;
            if (*p=='x') execute=1;
            ++p;
        }
        if (*p++!='"') return -1;
        kind=alloc ? (execute ? 0 : 1) : 3;
        if (alloc && !execute && strstr(p,"nobits")) kind=2;
    }
    return select_section(ctx,name,kind);
}
static int data_string(struct context *ctx, char *s, int terminated)
{
    for (;;) {
        s=trim(s);
        if (*s++!='"') return -1;
        while (*s && *s!='"') {
            unsigned value=(unsigned char)*s++;
            if (value=='\\') {
                value=(unsigned char)*s++;
                if (!value) return -1;
                if (value>='0' && value<='7') {
                    value-='0';
                    for (unsigned i=1;i<3 && *s>='0' && *s<='7';++i) value=value*8+(unsigned)(*s++-'0');
                } else if (value=='x') {
                    int digit=hex_digit((unsigned char)*s);
                    if (digit<0) return -1;
                    value=0;
                    while ((digit=hex_digit((unsigned char)*s))>=0) {
                        if (value>(255u-(unsigned)digit)/16) return -1;
                        value=value*16+(unsigned)digit;++s;
                    }
                } else {
                    switch (value) {
                    case 'a':value=7;break;case 'b':value=8;break;
                    case 'f':value=12;break;case 'n':value=10;break;
                    case 'r':value=13;break;case 't':value=9;break;
                    case 'v':value=11;break;case '\\':case '"':break;
                    default:return -1;
                    }
                }
            }
            uint32_t at;
            if (value>255 || data_reserve(ctx,1,&at) ||
                cs_copy_constant(&ctx->program.image,at,8,value)) return -1;
        }
        if (*s++!='"') return -1;
        if (terminated) { uint32_t at;if (data_reserve(ctx,1,&at)) return -1; }
        s=trim(s);
        if (!*s) return 0;
        if (*s++!=',') return -1;
    }
}
/* 0: metadata handled by caller, 1: consumed, -1: invalid directive. */
static int data_directive(struct context *ctx, char *s)
{
    char *arguments=s;
    while (*arguments && !whitespace((unsigned char)*arguments)) ++arguments;
    char saved=*arguments;
    if (saved) *arguments++=0;
    arguments=trim(arguments);
    int result=1;
    if (!strcmp(s,".text") || !strcmp(s,".data") || !strcmp(s,".rodata") || !strcmp(s,".bss")) {
        int kind=!strcmp(s,".text") ? 0 : !strcmp(s,".bss") ? 2 : 1;
        if (select_section(ctx,s,kind)) return -1;
    } else if (!strcmp(s,".section") || !strcmp(s,".pushsection")) {
        unsigned previous=ctx->active_section;
        int push=!strcmp(s,".pushsection");
        if ((push && ctx->section_depth==16) || section_directive(ctx,arguments)) return -1;
        if (push) ctx->section_stack[ctx->section_depth++]=previous;
    } else if (!strcmp(s,".popsection") || !strcmp(s,".previous")) {
        if (*arguments || (!strcmp(s,".popsection") && !ctx->section_depth) ||
            (!strcmp(s,".previous") && !ctx->previous_valid)) return -1;
        unsigned next=!strcmp(s,".popsection") ? ctx->section_stack[--ctx->section_depth] : ctx->previous_section;
        ctx->previous_section=ctx->active_section;ctx->active_section=next;ctx->section=ctx->sections[next].kind;
        ctx->previous_valid=1;
    } else if (!strcmp(s,".set") || !strcmp(s,".equ")) {
        char *comma=strchr(arguments,',');
        if (!comma || ctx->alias_count==CS_COPY_LABEL_CAPACITY) return -1;
        *comma++=0;
        int index=label(ctx,trim(arguments)),target=-1;uint32_t addend;
        if (index<0 || ctx->labels[index].defined || ctx->labels[index].alias) return -1;
        if (integer(trim(comma),&addend) && expression(ctx,trim(comma),&target,&addend)) return -1;
        unsigned i=ctx->alias_count++;
        ctx->aliases[i].label=index;ctx->aliases[i].target=target;ctx->aliases[i].addend=addend;
        ctx->labels[index].alias=1;
    } else if (!strcmp(s,".comm")) {
        unsigned previous=ctx->previous_section,active=ctx->active_section;
        int previous_valid=ctx->previous_valid;
        if (select_section(ctx,".bss",2)) return -1;
        char *comma=strchr(arguments,',');
        if (!comma) return -1;
        *comma++=0;
        char *align=strchr(comma,',');uint32_t count,alignment=4,at;
        if (align) { *align++=0;if (integer(trim(align),&alignment)) return -1; }
        int index=label(ctx,trim(arguments));
        if (index<0 || ctx->labels[index].defined || ctx->labels[index].alias || integer(trim(comma),&count) ||
            data_align(ctx,alignment)) return -1;
        ctx->labels[index].address=ctx->sections[ctx->active_section].position;
        ctx->labels[index].data=(int)ctx->active_section+1;ctx->labels[index].defined=1;
        if (data_reserve(ctx,count,&at)) return -1;
        ctx->active_section=active;ctx->previous_section=previous;ctx->section=ctx->sections[active].kind;
        ctx->previous_valid=previous_valid;
    } else if (!strcmp(s,".weak")) {
        for (;;) {
            char *comma=strchr(arguments,',');if (comma) *comma=0;
            int index=label(ctx,trim(arguments));
            if (index<0) return -1;
            ctx->labels[index].weak=1;
            if (!comma) break;
            arguments=comma+1;
        }
    } else if (!strcmp(s,".local") || !strcmp(s,".hidden") || !strcmp(s,".protected")) {
        if (!*arguments) return -1;
    } else if (ctx->section==1 || ctx->section==2) {
        uint32_t count,at;
        if (!strcmp(s,".align") || !strcmp(s,".p2align") || !strcmp(s,".balign")) {
            if (integer(arguments,&count)) return -1;
            if (strcmp(s,".balign")) { if (count>30) return -1;count=1u<<count; }
            if (data_align(ctx,count)) return -1;
        } else if (!strcmp(s,".zero") || !strcmp(s,".space") || !strcmp(s,".skip")) {
            if (integer(arguments,&count) || data_reserve(ctx,count,&at)) return -1;
        } else if (!strcmp(s,".ascii") || !strcmp(s,".string") || !strcmp(s,".asciz")) {
            if (ctx->section==2 || data_string(ctx,arguments,strcmp(s,".ascii")!=0)) return -1;
        } else {
            unsigned bytes=!strcmp(s,".byte") ? 1 : (!strcmp(s,".short") || !strcmp(s,".2byte")) ? 2 :
                (!strcmp(s,".long") || !strcmp(s,".word") || !strcmp(s,".4byte")) ? 4 :
                (!strcmp(s,".quad") || !strcmp(s,".8byte")) ? 8 : 0;
            if (!bytes) result=0;
            else for (;;) {
                char *comma=strchr(arguments,',');if (comma) *comma=0;
                char *value=trim(arguments);uint64_t number;
                if (data_reserve(ctx,bytes,&at)) return -1;
                if (!integer64(value,&number)) {
                    if (ctx->section==2 && number) return -1;
                    if (cs_copy_constant(&ctx->program.image,at,bytes>4 ? 32 : bytes*8,(uint32_t)number) ||
                        (bytes==8 && cs_copy_constant(&ctx->program.image,at+32,32,(uint32_t)(number>>32)))) return -1;
                } else {
                    int index,subtract;uint64_t addend;
                    if (ctx->section==2 || bytes<4 || ctx->relocation_count==CS_COPY_RELOCATION_CAPACITY ||
                        data_expression(ctx,value,&index,&subtract,&addend)) return -1;
                    unsigned i=ctx->relocation_count++;
                    ctx->relocations[i].destination=at;ctx->relocations[i].addend=addend;ctx->relocations[i].label=index;
                    ctx->relocations[i].subtract=subtract;ctx->relocations[i].bytes=bytes;
                }
                if (!comma) break;
                arguments=comma+1;
            }
        }
    } else result=0;
    if (!result && saved) {
        /* Restore token separation before the metadata fallback. */
        s[strlen(s)]=saved;
    }
    return result;
}
static void strip_comment(char *s)
{
    int quoted=0,escaped=0;
    for (;*s;++s) {
        if (escaped) escaped=0;
        else if (quoted && *s=='\\') escaped=1;
        else if (*s=='"') quoted=!quoted;
        else if (!quoted && *s=='#') { *s=0;break; }
    }
}
static int layout_data(struct context *ctx)
{
    uint32_t cursor=256;
    for (unsigned i=0;i<ctx->section_count;++i) {
        if (ctx->sections[i].kind!=1 && ctx->sections[i].kind!=2) continue;
        uint32_t align=ctx->sections[i].alignment;
        cursor=(cursor+align-1)&~(align-1);
        uint32_t capacity=ctx->memory_bytes/2;
        if (cursor>capacity || ctx->sections[i].position>capacity-cursor) return -1;
        ctx->sections[i].base=cursor;cursor+=ctx->sections[i].position;
    }
    for (unsigned i=0;i<ctx->label_count;++i)
        if (ctx->labels[i].defined && ctx->labels[i].data>0)
            ctx->labels[i].address+=ctx->sections[ctx->labels[i].data-1].base;
    for (unsigned i=0;i<ctx->label_count;++i)
        if (ctx->labels[i].weak && !ctx->labels[i].defined && !ctx->labels[i].alias) {
            ctx->labels[i].defined=1;ctx->labels[i].data=-1;
            ctx->labels[i].address=0;ctx->labels[i].missing_weak=1;
        }
    for (unsigned pass=0;pass<ctx->alias_count;++pass)
        for (unsigned i=0;i<ctx->alias_count;++i) {
            int index=ctx->aliases[i].label,target=ctx->aliases[i].target;
            if (ctx->labels[index].defined || (target>=0 && !ctx->labels[target].defined)) continue;
            ctx->labels[index].address=ctx->aliases[i].addend+(target<0 ? 0 : ctx->labels[target].address);
            ctx->labels[index].data=target<0 ? -1 : ctx->labels[target].data;
            ctx->labels[index].missing_weak=target>=0 && ctx->labels[target].missing_weak;
            ctx->labels[index].defined=1;
        }
    for (unsigned i=0;i<ctx->alias_count;++i)
        if (!ctx->labels[ctx->aliases[i].label].defined) return -1;
    return 0;
}
static void pack_data(struct context *ctx)
{
    unsigned char *staging=ctx->program.image.data+ctx->data_begin/8;
    uint32_t capacity=ctx->memory_bytes/2;
    unsigned char *packed=staging+capacity;
    memset(packed,0,capacity);
    for (unsigned i=0;i<ctx->fragment_count;++i)
        memcpy(packed+ctx->sections[ctx->fragments[i].section].base+ctx->fragments[i].offset,
               staging+ctx->fragments[i].staging,ctx->fragments[i].count);
    memcpy(staging,packed,capacity);
    memset(packed,0,capacity);
}
static int symbol(struct context *ctx, const char *name, uint32_t *address)
{
    int index;uint32_t addend;
    if (expression(ctx,name,&index,&addend)) return -1;
    unsigned i;
    for (i=0;i<ctx->symbol_count;++i)
        if (ctx->symbols[i].label==index && ctx->symbols[i].addend==addend) break;
    if (i==ctx->symbol_count) {
        if (i==CS_COPY_SYMBOL_CAPACITY) return -1;
        ctx->symbols[i].label=index;ctx->symbols[i].addend=addend;++ctx->symbol_count;
    }
    *address=SYMBOL_TABLE+32*i;
    return 0;
}
static int metadata(const char *s)
{
    const char *names[]={".text", ".file", ".ident", ".p2align", ".align",
                         ".global", ".globl", ".type", ".size"};
    for (unsigned i=0;i<sizeof(names)/sizeof(names[0]);++i) {
        size_t n=strlen(names[i]);
        if (!strncmp(s,names[i],n) && (!s[n] || whitespace((unsigned char)s[n]))) return 1;
    }
    if (!strncmp(s,".section",8) && whitespace((unsigned char)s[8])) {
        s+=8; while (whitespace((unsigned char)*s)) ++s;
        if (!strncmp(s,".text",5) && (!s[5] || s[5]=='.' || s[5]==',' || whitespace((unsigned char)s[5]))) return 1;
        if (!strncmp(s,".note.GNU-stack",15) && (!s[15] || s[15]==',' || whitespace((unsigned char)s[15]))) return 1;
    }
    return 0;
}
static int lookup(struct context *ctx, uint32_t destination, uint32_t table,
                  uint32_t a, uint32_t b, uint32_t c, unsigned inputs)
{
    struct cs_copy_program *p=&ctx->program;
    if (p->image.slot>255-inputs-1 && cs_copy_program_next(p)) return -1;
    uint32_t source_field=(p->image.slot+inputs)*p->image.instruction_bits+
                          p->image.count_bits+p->image.address_bits;
    if (cs_copy_program_emit(p,1,source_field,a) ||
        cs_copy_program_emit(p,1,source_field+1,b) ||
        (inputs==3 && cs_copy_program_emit(p,1,source_field+2,c))) return -1;
    return cs_copy_program_emit(p,1,destination,table);
}
static int compare32(struct context *ctx, uint32_t left, uint32_t right)
{
    struct cs_copy_program *p=&ctx->program;
    if (cs_copy_program_emit(p,1,CMP_EQ,EQ_TABLE+7) ||
        cs_copy_program_emit(p,1,CMP_LTU,EQ_TABLE)) return -1;
    for (unsigned bit=0;bit<32;++bit)
        if (lookup(ctx,CMP_LTU,LT_TABLE,left+bit,right+bit,CMP_LTU,3) ||
            lookup(ctx,CMP_EQ,EQ_TABLE,left+bit,right+bit,CMP_EQ,3)) return -1;
    if (lookup(ctx,CMP_SIGN,XOR_TABLE,left+31,right+31,0,2) ||
        lookup(ctx,CMP_LTS,XOR_TABLE,CMP_SIGN,CMP_LTU,0,2) ||
        lookup(ctx,CMP_LEU,OR_TABLE,CMP_LTU,CMP_EQ,0,2) ||
        lookup(ctx,CMP_LES,OR_TABLE,CMP_LTS,CMP_EQ,0,2)) return -1;
    ctx->compared=1;
    return 0;
}
static const char *conditional_jump(struct context *ctx, int index,
                                   uint32_t flag, int inverted, size_t line)
{
    if (ctx->jump_count==CS_COPY_JUMP_CAPACITY) return "jump capacity exceeded";
    struct cs_copy_program *p=&ctx->program;
    if (p->image.slot>253 && cs_copy_program_next(p)) return "copy image capacity exceeded";
    uint32_t table=BRANCH_TABLE+64*ctx->jump_count;
    uint32_t read_field=(p->image.slot+1)*p->image.instruction_bits+
                        p->image.count_bits+p->image.address_bits;
    uint32_t jump_field=255*p->image.instruction_bits+p->image.count_bits+p->image.address_bits;
    if (cs_copy_program_emit(p,1,read_field+5,flag) ||
        cs_copy_program_emit(p,p->image.address_bits,jump_field,table)) return "copy image capacity exceeded";
    unsigned i=ctx->jump_count;
    if (jump(ctx,index,line)) return "copy image capacity exceeded";
    ctx->jumps[i].table=table;
    ctx->jumps[i].inverted=inverted;
    ctx->jumps[i].fallthrough=p->image.layer;
    return NULL;
}
static const char *branch(struct context *ctx, char *s, size_t line)
{
    static const struct { const char *name; uint32_t flag; int inverted; } conditions[]={
        {"eq",CMP_EQ,0},{"ne",CMP_EQ,1},{"lt",CMP_LTS,0},{"ge",CMP_LTS,1},
        {"le",CMP_LES,0},{"gt",CMP_LES,1},{"ltu",CMP_LTU,0},{"geu",CMP_LTU,1},
        {"leu",CMP_LEU,0},{"gtu",CMP_LEU,1}};
    if (!ctx->compared) return "conditional branch without comparison";
    char *operand=s;
    while (*operand && !whitespace((unsigned char)*operand)) ++operand;
    if (*operand) *operand++=0;
    unsigned kind;
    for (kind=0;kind<sizeof(conditions)/sizeof(conditions[0]);++kind)
        if (!strcmp(s+12,conditions[kind].name)) break;
    if (kind==sizeof(conditions)/sizeof(conditions[0])) return "invalid branch condition";
    int index=label(ctx,trim(operand));
    if (index<0) return "invalid copy jump label";
    return conditional_jump(ctx,index,conditions[kind].flag,conditions[kind].inverted,line);
}
static int multiply32(struct context *ctx, uint32_t destination, uint32_t source)
{
    struct cs_copy_program *p=&ctx->program;
    uint32_t zero,one;
    if (ctx->label_count==CS_COPY_LABEL_CAPACITY || constant(ctx,0,&zero) || constant(ctx,1,&one)) return -1;
    if (cs_copy_program_emit(p,32,MUL_LEFT,destination) ||
        cs_copy_program_emit(p,32,MUL_RIGHT,source) ||
        cs_copy_program_emit(p,32,MUL_ACC,zero) ||
        cs_copy_program_emit(p,32,MUL_MARKER,one) || cs_copy_program_next(p)) return -1;
    unsigned loop=ctx->label_count++;
    ctx->labels[loop].defined=1;
    ctx->labels[loop].address=p->image.layer;
    for (unsigned bit=0;bit<32;++bit)
        if (lookup(ctx,MUL_ADDEND+bit,AND_TABLE,MUL_LEFT+bit,MUL_RIGHT,0,2)) return -1;
    if (cs_copy_program_add32(p,MUL_ACC,MUL_ACC,MUL_ADDEND,ADD_TABLE,TEMPORARY,CARRY) ||
        cs_copy_program_emit(p,1,MUL_STOP,MUL_MARKER+31) ||
        cs_copy_program_emit(p,31,MUL_LEFT+1,MUL_LEFT) ||
        cs_copy_program_emit(p,1,MUL_LEFT,zero) ||
        cs_copy_program_emit(p,31,MUL_RIGHT,MUL_RIGHT+1) ||
        cs_copy_program_emit(p,1,MUL_RIGHT+31,zero) ||
        cs_copy_program_emit(p,31,MUL_MARKER+1,MUL_MARKER) ||
        cs_copy_program_emit(p,1,MUL_MARKER,zero) ||
        conditional_jump(ctx,(int)loop,MUL_STOP,1,0)) return -1;
    return cs_copy_program_emit(p,32,destination,MUL_ACC);
}
static int internal_label(struct context *ctx)
{
    if (ctx->label_count==CS_COPY_LABEL_CAPACITY) return -1;
    return (int)ctx->label_count++;
}
static int bind_internal(struct context *ctx, int index)
{
    if (index<0 || cs_copy_program_next(&ctx->program)) return -1;
    ctx->labels[index].defined=1;
    ctx->labels[index].address=ctx->program.image.layer;
    return 0;
}
static int absolute32(struct context *ctx, uint32_t value, uint32_t sign, uint32_t zero)
{
    int skip=internal_label(ctx);
    return skip<0 || conditional_jump(ctx,skip,sign,1,0) ||
        cs_copy_program_sub32(&ctx->program,value,zero,value,SUB_TABLE,TEMPORARY,CARRY) ||
        bind_internal(ctx,skip) ? -1 : 0;
}
static int divide32(struct context *ctx, uint32_t destination, uint32_t source,
                    int signed_operation, int remainder)
{
    struct cs_copy_program *p=&ctx->program;
    uint32_t zero,one;
    int compared=ctx->compared;
    if (constant(ctx,0,&zero) || constant(ctx,1,&one) ||
        cs_copy_program_emit(p,5,DIV_FLAGS,CMP_EQ) ||
        cs_copy_program_emit(p,32,DIV_NUM,destination) ||
        cs_copy_program_emit(p,32,DIV_DEN,source) ||
        cs_copy_program_emit(p,1,DIV_NUM_SIGN,DIV_NUM+31) ||
        cs_copy_program_emit(p,1,DIV_DEN_SIGN,DIV_DEN+31)) return -1;
    if (signed_operation &&
        (absolute32(ctx,DIV_NUM,DIV_NUM_SIGN,zero) ||
         absolute32(ctx,DIV_DEN,DIV_DEN_SIGN,zero))) return -1;
    if (cs_copy_program_emit(p,32,DIV_REM,zero) ||
        cs_copy_program_emit(p,32,DIV_QUO,zero) ||
        cs_copy_program_emit(p,32,DIV_MARK,one) || cs_copy_program_next(p)) return -1;
    int loop=internal_label(ctx),skip=internal_label(ctx);
    if (loop<0 || skip<0) return -1;
    ctx->labels[loop].defined=1;ctx->labels[loop].address=p->image.layer;
    if (cs_copy_program_emit(p,1,DIV_OVERFLOW,DIV_REM+31) ||
        cs_copy_program_emit(p,31,DIV_REM+1,DIV_REM) ||
        cs_copy_program_emit(p,1,DIV_REM,DIV_NUM+31) ||
        cs_copy_program_emit(p,31,DIV_NUM+1,DIV_NUM) ||
        cs_copy_program_emit(p,1,DIV_NUM,zero) ||
        cs_copy_program_emit(p,31,DIV_QUO+1,DIV_QUO) ||
        cs_copy_program_emit(p,1,DIV_QUO,zero) ||
        compare32(ctx,DIV_REM,DIV_DEN) ||
        lookup(ctx,DIV_REDUCE,XOR_TABLE,CMP_LTU,one,0,2) ||
        lookup(ctx,DIV_REDUCE,OR_TABLE,DIV_REDUCE,DIV_OVERFLOW,0,2) ||
        conditional_jump(ctx,skip,DIV_REDUCE,1,0) ||
        cs_copy_program_sub32(p,DIV_REM,DIV_REM,DIV_DEN,SUB_TABLE,TEMPORARY,CARRY) ||
        cs_copy_program_emit(p,1,DIV_QUO,one) || bind_internal(ctx,skip) ||
        cs_copy_program_emit(p,1,DIV_STOP,DIV_MARK+31) ||
        cs_copy_program_emit(p,31,DIV_MARK+1,DIV_MARK) ||
        cs_copy_program_emit(p,1,DIV_MARK,zero) ||
        conditional_jump(ctx,loop,DIV_STOP,1,0)) return -1;
    uint32_t result=remainder ? DIV_REM : DIV_QUO;
    if (signed_operation) {
        if (remainder) {
            if (cs_copy_program_emit(p,1,DIV_SIGN,DIV_NUM_SIGN)) return -1;
        } else if (lookup(ctx,DIV_SIGN,XOR_TABLE,DIV_NUM_SIGN,DIV_DEN_SIGN,0,2)) return -1;
        /* Preserve the division-by-zero sentinel for signed quotient too. */
        if (!remainder) {
            if (compare32(ctx,DIV_DEN,zero) ||
                lookup(ctx,DIV_DEN_SIGN,XOR_TABLE,CMP_EQ,one,0,2) ||
                lookup(ctx,DIV_SIGN,AND_TABLE,DIV_SIGN,DIV_DEN_SIGN,0,2)) {
                return -1;
            }
        }
        if (absolute32(ctx,result,DIV_SIGN,zero)) return -1;
    }
    if (cs_copy_program_emit(p,32,destination,result) ||
        cs_copy_program_emit(p,5,CMP_EQ,DIV_FLAGS)) return -1;
    ctx->compared=compared;
    return 0;
}
static int shift32(struct context *ctx, int right, int arithmetic,
                   uint32_t destination, uint32_t count)
{
    struct cs_copy_program *p=&ctx->program;
    if (cs_copy_program_emit(p,5,SHIFT_COUNT,count)) return -1;
    for (unsigned stage=0;stage<5;++stage) {
        unsigned step=1u<<stage;
        if (cs_copy_program_emit(p,32,SHIFT_WORD,destination)) return -1;
        for (unsigned bit=0;bit<32;++bit) {
            uint32_t selected=SHIFT_ZERO;
            if (right) {
                if (bit+step<32) selected=SHIFT_WORD+bit+step;
                else if (arithmetic) selected=SHIFT_WORD+31;
            } else if (bit>=step) selected=SHIFT_WORD+bit-step;
            /* The selector and its read must remain in the same layer. */
            if (p->image.slot>251 && cs_copy_program_next(p)) return -1;
            uint32_t source_field=(p->image.slot+3)*p->image.instruction_bits+
                                  p->image.count_bits+p->image.address_bits;
            if (cs_copy_program_emit(p,1,SHIFT_PAIR,SHIFT_WORD+bit) ||
                cs_copy_program_emit(p,1,SHIFT_PAIR+1,selected) ||
                cs_copy_program_emit(p,1,source_field,SHIFT_COUNT+stage) ||
                cs_copy_program_emit(p,1,destination+bit,SHIFT_PAIR)) return -1;
        }
    }
    return 0;
}
static const char *memory_access(struct context *ctx, int store, unsigned width,
                                 uint32_t value, uint32_t base, uint32_t offset)
{
    struct cs_copy_program *p=&ctx->program;
    if (!ctx->data_begin) {
        uint32_t bits=(uint32_t)(p->image.bytes*8);
        if (bits<524288 || (bits&65535)) return "memory requires an aligned image of at least 64 KiB";
        ctx->data_begin=bits-65536;
        if (p->code_end>ctx->data_begin) return "memory overlaps generated code";
        p->code_limit=ctx->data_begin;
        ctx->memory_fault=internal_label(ctx);
        if (ctx->memory_fault<0) return "label capacity exceeded";
    }
    if (cs_copy_program_emit(p,32,MEM_ADDRESS,base)) return "copy image capacity exceeded";
    if (offset) {
        uint32_t addend;
        if (constant(ctx,offset,&addend) || cs_copy_program_add32(p,MEM_ADDRESS,MEM_ADDRESS,addend,ADD_TABLE,TEMPORARY,CARRY))
            return "copy image capacity exceeded";
    }
    uint32_t limit;
    int compared=ctx->compared;
    if (constant(ctx,ctx->memory_bytes-width/8,&limit) ||
        cs_copy_program_emit(p,5,MEM_FLAGS,CMP_EQ) || compare32(ctx,MEM_ADDRESS,limit) ||
        cs_copy_program_emit(p,1,MEM_VALID,CMP_LEU) ||
        cs_copy_program_emit(p,5,CMP_EQ,MEM_FLAGS) ||
        conditional_jump(ctx,ctx->memory_fault,MEM_VALID,1,0)) return "copy image capacity exceeded";
    ctx->compared=compared;
    if (cs_copy_constant(&p->image,MEM_BIT_ADDRESS,p->image.address_bits,ctx->data_begin) ||
        cs_copy_program_emit(p,ctx->memory_address_bits,MEM_BIT_ADDRESS+3,MEM_ADDRESS)) return "copy image capacity exceeded";
    if (!store && width<32) {
        uint32_t zero;
        if (constant(ctx,0,&zero) || cs_copy_program_emit(p,32-width,value+width,zero)) return "copy image capacity exceeded";
    }
    if (p->image.slot>253 && cs_copy_program_next(p)) return "copy image capacity exceeded";
    uint32_t field=(p->image.slot+1)*p->image.instruction_bits+p->image.count_bits;
    if (!store) field+=p->image.address_bits;
    if (cs_copy_program_emit(p,p->image.address_bits,field,MEM_BIT_ADDRESS) ||
        cs_copy_program_emit(p,width,store ? ctx->data_begin : value,store ? value : ctx->data_begin))
        return "copy image capacity exceeded";
    return NULL;
}
static const char *memory(struct context *ctx, const char *operation, char *left, char *right)
{
    size_t length=strlen(operation);
    unsigned width=operation[length-1]=='b' ? 8 : operation[length-1]=='s' ? 16 : 32;
    int store=operation[5]=='s';
    char *address=store ? left : right;
    uint32_t value,base,offset=0;
    if (reg(store ? right : left,&value)) return "invalid memory value register";
    char *open=strchr(address,'(');
    if (open) {
        char *close=strchr(open,')');
        if (!close || *trim(close+1)) return "invalid memory address";
        *open=0;*close=0;
        char *displacement=trim(address);
        if ((*displacement && integer(displacement,&offset)) || reg(trim(open+1),&base)) return "invalid memory address";
    } else {
        uint32_t absolute;
        if (integer(address,&absolute)) {
            if (!ctx->program_mode || symbol(ctx,address,&base)) return "invalid absolute memory address";
        } else if (constant(ctx,absolute,&base)) return "constant capacity exceeded";
    }
    return memory_access(ctx,store,width,value,base,offset);
}
static const char *stack(struct context *ctx, int push, char *cursor, char *operand)
{
    uint32_t pointer,value,four;
    if (reg(cursor,&pointer) || reg(operand,&value)) return "invalid stack register";
    if (constant(ctx,4,&four)) return "constant capacity exceeded";
    struct cs_copy_program *p=&ctx->program;
    if (push) {
        if (cs_copy_program_emit(p,32,STACK_VALUE,value) ||
            cs_copy_program_sub32(p,pointer,pointer,four,SUB_TABLE,TEMPORARY,CARRY)) return "copy image capacity exceeded";
        return memory_access(ctx,1,32,STACK_VALUE,pointer,0);
    }
    const char *error=memory_access(ctx,0,32,STACK_VALUE,pointer,0);
    if (error) return error;
    if (cs_copy_program_add32(p,pointer,pointer,four,ADD_TABLE,TEMPORARY,CARRY) ||
        cs_copy_program_emit(p,32,value,STACK_VALUE)) return "copy image capacity exceeded";
    return NULL;
}
static int dynamic_jump(struct context *ctx, uint32_t address)
{
    struct cs_copy_program *p=&ctx->program;
    uint32_t source_field=255*p->image.instruction_bits+p->image.count_bits+p->image.address_bits;
    return cs_copy_program_emit(p,p->image.address_bits,source_field,address) ||
           cs_copy_program_next(p) ? -1 : 0;
}
static const char *call(struct context *ctx, char *name, size_t line, int indirect)
{
    if (ctx->call_count==CS_COPY_CALL_CAPACITY) return "call capacity exceeded";
    int target=-1;
    struct cs_copy_program *p=&ctx->program;
    if (indirect) {
        uint32_t source;
        if (reg(name,&source)) return "invalid indirect function register";
        if (cs_copy_program_emit(p,32,CALL_TARGET,source)) return "copy image capacity exceeded";
    } else {
        target=label(ctx,name);
        if (target<0) return "invalid function label";
    }
    uint32_t twelve;
    uint32_t continuation=CALL_TABLE+32*ctx->call_count++;
    /* The caller writes its static chain at old SP-4.  After allocating
       the 12-byte frame this is FP+8, where the callee expects it. */
    if (constant(ctx,12,&twelve) ||
        cs_copy_program_sub32(p,REG_BASE+32,REG_BASE+32,twelve,SUB_TABLE,TEMPORARY,CARRY) ||
        memory_access(ctx,1,32,REG_BASE,REG_BASE+32,0) ||
        memory_access(ctx,1,32,continuation,REG_BASE+32,4) ||
        cs_copy_program_emit(p,32,REG_BASE,REG_BASE+32) ||
        (indirect ? dynamic_jump(ctx,CALL_TARGET) : jump(ctx,target,line)) ||
        cs_copy_constant(&p->image,continuation,32,p->image.layer)) return "copy image capacity exceeded";
    return NULL;
}
static int return_frame(struct context *ctx)
{
    struct cs_copy_program *p=&ctx->program;
    uint32_t twelve;
    if (constant(ctx,12,&twelve) ||
        memory_access(ctx,0,32,RETURN_FP,REG_BASE,0) ||
        memory_access(ctx,0,32,RETURN_PC,REG_BASE,4) ||
        cs_copy_program_add32(p,REG_BASE+32,REG_BASE,twelve,ADD_TABLE,TEMPORARY,CARRY) ||
        cs_copy_program_emit(p,32,REG_BASE,RETURN_FP)) return -1;
    return dynamic_jump(ctx,RETURN_PC);
}
static const char *instruction(struct context *ctx, char *s)
{
    char *operands=s;
    while (*operands && !whitespace((unsigned char)*operands)) ++operands;
    if (*operands) *operands++=0;
    operands=trim(operands);
    if (!strcmp(s,"copy.nop")) return *operands ? "unexpected operand" : NULL;
    char *comma=strchr(operands,',');
    if (!comma) return "two operands required";
    *comma++=0;
    if (!strcmp(s,"copy.push") || !strcmp(s,"copy.pop"))
        return stack(ctx,!strcmp(s,"copy.push"),trim(operands),trim(comma));
    const char *memory_ops[]={"copy.ld.b","copy.ld.s","copy.ld.l","copy.lda.b","copy.lda.s","copy.lda.l",
        "copy.ldo.b","copy.ldo.s","copy.ldo.l","copy.st.b","copy.st.s","copy.st.l",
        "copy.sta.b","copy.sta.s","copy.sta.l","copy.sto.b","copy.sto.s","copy.sto.l"};
    for (unsigned i=0;i<sizeof(memory_ops)/sizeof(memory_ops[0]);++i)
        if (!strcmp(s,memory_ops[i])) return memory(ctx,s,trim(operands),trim(comma));
    uint32_t destination, source;
    if (reg(trim(operands),&destination)) return "invalid destination register";
    char *argument=trim(comma);
    int rc;
    int load_constant=!strcmp(s,"copy.ldi.l") || !strcmp(s,"copy.ldi.b") || !strcmp(s,"copy.ldi.s");
    if (load_constant || !strcmp(s,"copy.inc") || !strcmp(s,"copy.dec")) {
        uint32_t value;
        if (integer(argument,&value)) {
            if (!ctx->program_mode || strcmp(s,"copy.ldi.l") || symbol(ctx,argument,&source))
                return "invalid 32-bit integer or symbol";
            return cs_copy_program_emit(&ctx->program,32,destination,source) ? "copy image capacity exceeded" : NULL;
        }
        if (!strcmp(s,"copy.ldi.b")) value&=255;
        else if (!strcmp(s,"copy.ldi.s")) value&=65535;
        if (constant(ctx,value,&source)) return "constant capacity exceeded";
        if (load_constant) rc=cs_copy_program_emit(&ctx->program,32,destination,source);
        else if (!strcmp(s,"copy.inc")) rc=cs_copy_program_add32(&ctx->program,destination,destination,source,ADD_TABLE,TEMPORARY,CARRY);
        else rc=cs_copy_program_sub32(&ctx->program,destination,destination,source,SUB_TABLE,TEMPORARY,CARRY);
    } else {
        if (reg(argument,&source)) return "invalid source register";
        if (!strcmp(s,"copy.mov")) rc=cs_copy_program_emit(&ctx->program,32,destination,source);
        else if (!strcmp(s,"copy.zex.b") || !strcmp(s,"copy.zex.s") ||
                 !strcmp(s,"copy.sex.b") || !strcmp(s,"copy.sex.s")) {
            unsigned width=s[strlen(s)-1]=='b' ? 8 : 16;
            int signed_extension=s[5]=='s';
            rc=cs_copy_program_emit(&ctx->program,width,destination,source);
            if (!rc && signed_extension) {
                for (unsigned bit=width;bit<32 && !rc;++bit)
                    rc=cs_copy_program_emit(&ctx->program,1,destination+bit,destination+width-1);
            } else if (!rc) {
                uint32_t zero;
                rc=constant(ctx,0,&zero);
                if (!rc) rc=cs_copy_program_emit(&ctx->program,32-width,destination+width,zero);
            }
        }
        else if (!strcmp(s,"copy.cmp")) rc=compare32(ctx,destination,source);
        else if (!strcmp(s,"copy.mul")) rc=multiply32(ctx,destination,source);
        else if (!strcmp(s,"copy.udiv") || !strcmp(s,"copy.umod") ||
                 !strcmp(s,"copy.div") || !strcmp(s,"copy.mod"))
            rc=divide32(ctx,destination,source,!strcmp(s,"copy.div") || !strcmp(s,"copy.mod"),
                        !strcmp(s,"copy.mod") || !strcmp(s,"copy.umod"));
        else if (!strcmp(s,"copy.neg") || !strcmp(s,"copy.not")) {
            uint32_t immutable;
            int invert=!strcmp(s,"copy.not");
            if (constant(ctx,invert ? UINT32_MAX : 0,&immutable)) return "constant capacity exceeded";
            if (invert) rc=cs_copy_program_bits32(&ctx->program,CS_COPY_XOR,destination,source,immutable,XOR_TABLE);
            else rc=cs_copy_program_sub32(&ctx->program,destination,immutable,source,SUB_TABLE,TEMPORARY,CARRY);
        }
        else if (!strcmp(s,"copy.add")) rc=cs_copy_program_add32(&ctx->program,destination,destination,source,ADD_TABLE,TEMPORARY,CARRY);
        else if (!strcmp(s,"copy.sub")) rc=cs_copy_program_sub32(&ctx->program,destination,destination,source,SUB_TABLE,TEMPORARY,CARRY);
        else if (!strcmp(s,"copy.and")) rc=cs_copy_program_bits32(&ctx->program,CS_COPY_AND,destination,destination,source,AND_TABLE);
        else if (!strcmp(s,"copy.or")) rc=cs_copy_program_bits32(&ctx->program,CS_COPY_OR,destination,destination,source,OR_TABLE);
        else if (!strcmp(s,"copy.xor")) rc=cs_copy_program_bits32(&ctx->program,CS_COPY_XOR,destination,destination,source,XOR_TABLE);
        else if (!strcmp(s,"copy.ashl")) rc=shift32(ctx,0,0,destination,source);
        else if (!strcmp(s,"copy.lshr")) rc=shift32(ctx,1,0,destination,source);
        else if (!strcmp(s,"copy.ashr")) rc=shift32(ctx,1,1,destination,source);
        else return "unsupported operation";
    }
    return rc ? "copy image capacity exceeded" : NULL;
}

/* Return an operator boundary, retaining a terminating label colon. */
static size_t statement_end(const char *assembly, size_t size, size_t begin, size_t *next)
{
    int quoted=0,escaped=0;
    for (size_t i=begin;i<size;++i) {
        unsigned char c=(unsigned char)assembly[i];
        if (c=='\n') { *next=i+1;return i; }
        if (escaped) { escaped=0;continue; }
        if (quoted && c=='\\') { escaped=1;continue; }
        if (c=='"') { quoted=!quoted;continue; }
        if (quoted) continue;
        if (c=='#') {
            size_t end=i;
            while (i<size && assembly[i]!='\n') ++i;
            *next=i+(i<size);return end;
        }
        if (c==';' || c==':') {
            *next=i+1;
            if (c==':' && *next<size && assembly[*next]=='\n') ++*next;
            return i+(c==':');
        }
    }
    *next=size;return size;
}
static size_t statement_capacity(const char *assembly, size_t size)
{
    size_t capacity=1,offset=0;
    while (offset<size) {
        size_t next,end=statement_end(assembly,size,offset,&next);
        if (end-offset==SIZE_MAX) return 0;
        if (end-offset+1>capacity) capacity=end-offset+1;
        offset=next;
    }
    return capacity;
}

static int link_image(unsigned char *data, size_t bytes, unsigned address_bits,
                       const char *assembly, size_t size, const char *entry,
                       const uint32_t *arguments, unsigned argc,
                       struct cs_copy_link_error *error, int program_mode, uint32_t memory_bytes)
{
    struct context ctx;
    char *buffer=NULL;
    const char *message="invalid link input";
    size_t line=0, offset=0, physical_line=1;
    int entered=0, returned=0, terminated=0, trapped=0;
    ctx.sections=NULL;ctx.fragments=NULL;
    if (!data || bytes<32768 || bytes>UINT32_MAX/8 || !assembly || !entry || !*entry ||
        argc>6 || (argc && !arguments) || memchr(assembly,0,size)) goto fail;
    message="out of memory for assembly operator";
    size_t capacity=statement_capacity(assembly,size);
    if (!capacity || !(buffer=malloc(capacity))) goto fail;
    memset(data,0,bytes);
    memset(&ctx,0,sizeof(ctx));
    message="invalid data/stack memory size";
    if (memory_bytes<8192 || (memory_bytes&(memory_bytes-1))) goto fail;
    ctx.assembly=assembly;ctx.assembly_size=size;ctx.statement_offset=SIZE_MAX;
    ctx.memory_bytes=memory_bytes;
    for (uint32_t n=memory_bytes; n>1; n>>=1) ++ctx.memory_address_bits;
    ctx.memory_fault=-1;
    ctx.program_mode=program_mode;
    ctx.data_cursor=256;
    if (cs_copy_program_init(&ctx.program,data,bytes,address_bits,CODE_BEGIN,(uint32_t)(bytes*8))) goto fail;
    if (cs_copy_constant(&ctx.program.image,EQ_TABLE,8,144) ||
        cs_copy_constant(&ctx.program.image,LT_TABLE,8,212) ||
        cs_copy_constant(&ctx.program.image,XOR_TABLE,4,6) ||
        cs_copy_constant(&ctx.program.image,AND_TABLE,4,8) ||
        cs_copy_constant(&ctx.program.image,OR_TABLE,4,14)) goto fail;
    if (cs_copy_constant(&ctx.program.image,REG_BASE,32,memory_bytes) ||
        cs_copy_constant(&ctx.program.image,REG_BASE+32,32,memory_bytes)) goto fail;
    for (unsigned i=0;i<argc;++i)
        if (cs_copy_constant(&ctx.program.image,REG_BASE+32*(i+2),32,arguments[i])) goto fail;
    int entry_label=-1;
    if (program_mode) {
        if (bytes<262144 || ((bytes*8)&65535)) goto fail;
        message="memory requires an aligned image with room for code";
        if (memory_bytes>=bytes || (bytes&(memory_bytes-1)) || bytes-memory_bytes<8192) goto fail;
        ctx.data_begin=(uint32_t)((bytes-memory_bytes)*8);
        ctx.program.code_limit=ctx.data_begin;
        if (select_section(&ctx,".text",0)) goto fail;
        entry_label=label(&ctx,entry);
        ctx.return_handler=internal_label(&ctx);
        ctx.memory_fault=internal_label(&ctx);
        if (entry_label<0 || ctx.return_handler<0 || ctx.memory_fault<0 ||
            /* GCC reserves six register-argument home words above its
             * 12-byte call frame, even when all arguments arrive in fields. */
            cs_copy_constant(&ctx.program.image,REG_BASE,32,memory_bytes-36) ||
            cs_copy_constant(&ctx.program.image,REG_BASE+32,32,memory_bytes-36) ||
            jump(&ctx,entry_label,0)) goto fail;
    }
    while (offset<size) {
        size_t next,end=statement_end(assembly,size,offset,&next);
        line=physical_line;
        ctx.statement_offset=offset;
        memcpy(buffer,assembly+offset,end-offset); buffer[end-offset]=0;
        for (size_t i=offset;i<next;++i) if (assembly[i]=='\n') ++physical_line;
        offset=next;
        char *s=trim(buffer);
        strip_comment(s);s=trim(s);
        if (!*s) continue;
        size_t length=strlen(s);
        if (s[length-1]==':') {
            s[length-1]=0;
            s=trim(s);
            const char *number_end;uint32_t number;
            int numbered=!decimal_label(s,&number_end,&number) && !*number_end;
            message="only one function and local labels are supported";
            if (!program_mode && ((!entered && strcmp(s,entry)) || (entered && !numbered && strncmp(s,".L",2)))) goto fail;
            int index=numbered ? numeric_label(&ctx,ctx.statement_offset) : label(&ctx,s);
            message="invalid or duplicate copy label";
            if (index<0 || ctx.labels[index].defined || ctx.labels[index].alias) goto fail;
            if (program_mode && ctx.section) {
                message="label outside text or data section";
                if (ctx.section!=1 && ctx.section!=2) goto fail;
                ctx.labels[index].address=ctx.sections[ctx.active_section].position;
                ctx.labels[index].data=(int)ctx.active_section+1;
                ctx.labels[index].defined=1;continue;
            }
            if (ctx.program.image.slot!=3 && cs_copy_program_next(&ctx.program)) {
                message="copy image capacity exceeded"; goto fail;
            }
            ctx.labels[index].address=ctx.program.image.layer;
            ctx.labels[index].defined=1;
            if (program_mode && !numbered && strncmp(s,".L",2)) ctx.compared=0;
            entered=1; terminated=0; continue;
        }
        if (*s=='.') {
            message="unsupported section or directive";
            if (program_mode) {
                int handled=data_directive(&ctx,s);
                if (handled<0) goto fail;
                if (handled) continue;
            }
            if (!metadata(s)) goto fail;
            continue;
        }
        message="operation outside leaf body";
        if (!entered || terminated || (program_mode && ctx.section)) goto fail;
        if (!strcmp(s,"copy.trap")) {
            message="copy image capacity exceeded";
            if (ctx.memory_fault<0) ctx.memory_fault=internal_label(&ctx);
            if (ctx.memory_fault<0 || jump(&ctx,ctx.memory_fault,line)) goto fail;
            trapped=1; terminated=1; continue;
        }
        if (!strcmp(s,"copy.ret")) {
            message="copy image capacity exceeded";
            if (jump(&ctx,program_mode ? ctx.return_handler : -2,line)) goto fail;
            returned=1; terminated=1; continue;
        }
        if (program_mode && !strncmp(s,"copy.jsra",9) && whitespace((unsigned char)s[9])) {
            message=call(&ctx,trim(s+9),line,0);
            if (message) goto fail;
            continue;
        }
        if (program_mode && !strncmp(s,"copy.jsr",8) && whitespace((unsigned char)s[8])) {
            message=call(&ctx,trim(s+8),line,1);
            if (message) goto fail;
            continue;
        }
        if (program_mode && !strncmp(s,"copy.jmp",8) && whitespace((unsigned char)s[8])) {
            uint32_t source;
            message="invalid indirect jump register";
            if (reg(trim(s+8),&source)) goto fail;
            message="copy image capacity exceeded";
            if (dynamic_jump(&ctx,source)) goto fail;
            terminated=1; continue;
        }
        if (!strncmp(s,"copy.branch.",12)) {
            message=branch(&ctx,s,line);
            if (message) goto fail;
            continue;
        }
        if (!strncmp(s,"copy.jmpa",9) && whitespace((unsigned char)s[9])) {
            int index=label(&ctx,trim(s+9));
            message="invalid copy jump label";
            if (index<0) goto fail;
            message="copy image capacity exceeded";
            if (jump(&ctx,index,line)) goto fail;
            terminated=1; continue;
        }
        message=instruction(&ctx,s);
        if (message) goto fail;
    }
    message="missing leaf entry or return";
    if (!entered || (!returned && !trapped)) goto fail;
    message="invalid section layout or unresolved alias";
    if (program_mode && (ctx.section_depth || layout_data(&ctx))) goto fail;
    if (program_mode && (!ctx.labels[entry_label].defined || ctx.labels[entry_label].data)) goto fail;
    message="copy image capacity exceeded";
    if (program_mode && (bind_internal(&ctx,ctx.return_handler) || return_frame(&ctx))) goto fail;
    if (ctx.memory_fault>=0) {
        if (jump(&ctx,-2,0) || bind_internal(&ctx,ctx.memory_fault)) goto fail;
        uint32_t fault=ctx.program.image.layer;
        if (cs_copy_program_next(&ctx.program)) goto fail;
        struct cs_copy_image stop=ctx.program.image;
        stop.layer=fault;
        if (cs_copy_row(&stop,255,stop.layer_bits,0,ZERO_LAYER)) goto fail;
    }
    if (cs_copy_program_next(&ctx.program)) goto fail;
    uint32_t report=ctx.program.image.layer;
    for (unsigned i=0;i<ctx.symbol_count;++i) {
        int index=ctx.symbols[i].label;
        message="undefined copy symbol";
        if (!ctx.labels[index].defined ||
            cs_copy_constant(&ctx.program.image,SYMBOL_TABLE+32*i,32,ctx.labels[index].address+ctx.symbols[i].addend)) goto fail;
    }
    for (unsigned i=0;i<ctx.relocation_count;++i) {
        int index=ctx.relocations[i].label,subtract=ctx.relocations[i].subtract;
        message="undefined data initializer symbol";
        if (!ctx.labels[index].defined || (subtract>=0 && !ctx.labels[subtract].defined)) goto fail;
        uint64_t value;
        if (subtract<0) value=(uint32_t)(ctx.labels[index].address+(uint32_t)ctx.relocations[i].addend);
        else value=(uint64_t)ctx.labels[index].address-ctx.labels[subtract].address+ctx.relocations[i].addend;
        if (cs_copy_constant(&ctx.program.image,ctx.relocations[i].destination,32,(uint32_t)value) ||
            (ctx.relocations[i].bytes==8 &&
             cs_copy_constant(&ctx.program.image,ctx.relocations[i].destination+32,32,(uint32_t)(value>>32)))) goto fail;
    }
    if (program_mode) {
        pack_data(&ctx);
        if (cs_copy_constant(&ctx.program.image,ctx.data_begin+(memory_bytes-36)*8,32,memory_bytes) ||
            cs_copy_constant(&ctx.program.image,ctx.data_begin+(memory_bytes-32)*8,32,report)) goto fail;
    }
    for (unsigned i=0;i<ctx.jump_count;++i) {
        int index=ctx.jumps[i].label;
        int missing_weak=index>=0 && ctx.labels[index].missing_weak;
        if (index>=0 && (!ctx.labels[index].defined || (ctx.labels[index].data && !missing_weak))) {
            line=ctx.jumps[i].line; message="undefined or non-code jump label"; goto fail;
        }
        uint32_t target=index==-2 ? report : missing_weak ? ctx.labels[ctx.memory_fault].address : ctx.labels[index].address;
        if (ctx.jumps[i].table) {
            uint32_t first=ctx.jumps[i].inverted ? target : ctx.jumps[i].fallthrough;
            uint32_t second=ctx.jumps[i].inverted ? ctx.jumps[i].fallthrough : target;
            if (cs_copy_constant(&ctx.program.image,ctx.jumps[i].table,32,first) ||
                cs_copy_constant(&ctx.program.image,ctx.jumps[i].table+32,32,second)) {
                message="invalid conditional copy jump table"; goto fail;
            }
            continue;
        }
        if (cs_copy_program_patch_jump(&ctx.program,ctx.jumps[i].layer,target)) {
            message="invalid copy jump target"; goto fail;
        }
    }
    message="copy image capacity exceeded";
    /* The synthetic caller releases its 24-byte argument area after return. */
    if (program_mode && cs_copy_program_emit(&ctx.program,32,REG_BASE+32,REG_BASE)) goto fail;
    for (unsigned i=0;i<32;++i)
        if (cs_copy_program_emit(&ctx.program,1,OUTPUT+(i/8)*8+7-(i%8),REG_BASE+64+i)) goto fail;
    if (cs_copy_program_next(&ctx.program) || cs_copy_row(&ctx.program.image,2,32,OUTPUT,STATUS) ||
        cs_copy_program_finish(&ctx.program,ZERO_LAYER)) goto fail;
    if (error) *error=(struct cs_copy_link_error){0,NULL};
    free(buffer);
    free(ctx.sections);free(ctx.fragments);
    return 0;
fail:
    free(buffer);
    free(ctx.sections);free(ctx.fragments);
    if (error) *error=(struct cs_copy_link_error){line,message};
    return -1;
}

int cs_copy_link_leaf(unsigned char *data, size_t bytes, unsigned address_bits,
                     const char *assembly, size_t size, const char *entry,
                     const uint32_t *arguments, unsigned argc, struct cs_copy_link_error *error)
{
    return link_image(data,bytes,address_bits,assembly,size,entry,arguments,argc,error,0,8192);
}

int cs_copy_link_program(unsigned char *data, size_t bytes, unsigned address_bits,
                        const char *assembly, size_t size, const char *entry,
                        const uint32_t *arguments, unsigned argc, struct cs_copy_link_error *error)
{
    return cs_copy_link_program_memory(data,bytes,address_bits,8192,assembly,size,entry,arguments,argc,error);
}

int cs_copy_link_program_memory(unsigned char *data, size_t bytes, unsigned address_bits,
                        uint32_t memory_bytes, const char *assembly, size_t size, const char *entry,
                        const uint32_t *arguments, unsigned argc, struct cs_copy_link_error *error)
{
    return link_image(data,bytes,address_bits,assembly,size,entry,arguments,argc,error,1,memory_bytes);
}

struct object_names {
    struct { char name[64]; unsigned defined,external,local,common,strong,weak,referenced;
             uint32_t common_size,common_alignment; } names[CS_COPY_LABEL_CAPACITY];
    unsigned count;
};
static int name_start(unsigned char c)
{
    return c=='_' || c=='.' || c=='$' || (c>='a' && c<='z') || (c>='A' && c<='Z');
}
static int name_char(unsigned char c) { return name_start(c) || (c>='0' && c<='9'); }
static int object_name(struct object_names *names, const char *s, size_t n, int create)
{
    if (!n || n>=sizeof(names->names[0].name) || !name_start((unsigned char)*s)) return -1;
    for (size_t i=1;i<n;++i) if (!name_char((unsigned char)s[i])) return -1;
    for (unsigned i=0;i<names->count;++i)
        if (strlen(names->names[i].name)==n && !memcmp(names->names[i].name,s,n)) return (int)i;
    if (!create || names->count==CS_COPY_LABEL_CAPACITY) return -1;
    unsigned i=names->count++;
    memcpy(names->names[i].name,s,n);names->names[i].name[n]=0;
    return (int)i;
}
static int object_line(const struct cs_copy_object *object, size_t *offset, char *buffer)
{
    size_t next,end=statement_end(object->assembly,object->size,*offset,&next);
    memcpy(buffer,object->assembly+*offset,end-*offset);buffer[end-*offset]=0;
    *offset=next;
    strip_comment(buffer);
    return 0;
}
static int object_references(struct object_names *names, const struct cs_copy_object *object, char *buffer)
{
    size_t offset=0;
    while (offset<object->size) {
        if (object_line(object,&offset,buffer)) return -1;
        char *s=trim(buffer);size_t length=strlen(s);
        if (!length || s[length-1]==':') continue;
        char *arguments=s;
        while (*arguments && !whitespace((unsigned char)*arguments)) ++arguments;
        if (*arguments) *arguments++=0;
        int data=*s=='.';
        if (data) {
            if (!strcmp(s,".set") || !strcmp(s,".equ")) {
                arguments=strchr(arguments,',');if (!arguments) return -1;++arguments;
            } else if (strcmp(s,".byte") && strcmp(s,".short") && strcmp(s,".2byte") &&
                       strcmp(s,".long") && strcmp(s,".word") && strcmp(s,".4byte") &&
                       strcmp(s,".quad") && strcmp(s,".8byte")) continue;
        }
        int direct=!strcmp(s,"copy.jsra") || !strcmp(s,"copy.jmpa") || !strncmp(s,"copy.branch.",12);
        int immediate=!strcmp(s,"copy.ldi.l");
        int memory=!strncmp(s,"copy.ld",7) || !strncmp(s,"copy.st",7);
        char *comma=strchr(arguments,',');
        char *at=arguments;int quoted=0,parentheses=0;
        while (*at) {
            if (*at=='"') quoted=!quoted;
            if (quoted && *at=='\\' && at[1]) { at+=2;continue; }
            if (!quoted && name_start((unsigned char)*at) &&
                (at==arguments || !name_char((unsigned char)at[-1]))) {
                char *end=at+1;
                while (name_char((unsigned char)*end)) ++end;
                size_t n=(size_t)(end-at);char name[64];uint32_t unused;
                if (n>=sizeof(name)) return -1;
                memcpy(name,at,n);name[n]=0;
                int symbolic=data || direct || (immediate && comma && at>comma);
                if (memory && comma && !parentheses && ((s[5]=='s') ? at<comma : at>comma)) symbolic=1;
                if (strcmp(name,".") && (symbolic || reg(name,&unused))) {
                    int index=object_name(names,name,n,1);
                    if (index<0) return -1;
                    names->names[index].referenced=1;
                }
                at=end;
            } else {
                if (!quoted && *at=='(') ++parentheses;
                if (!quoted && *at==')') --parentheses;
                ++at;
            }
        }
        if (quoted) return -1;
    }
    return 0;
}
static int object_scan(struct object_names *names, const struct cs_copy_object *object, char *buffer)
{
    size_t offset=0;
    unsigned depth=0;
    while (offset<object->size) {
        if (object_line(object,&offset,buffer)) return -1;
        char *s=trim(buffer);size_t length=strlen(s);
        if (!length) continue;
        if (s[length-1]==':') {
            s[length-1]=0;s=trim(s);
            const char *number_end;uint32_t number;
            if (!decimal_label(s,&number_end,&number) && !*number_end) continue;
            int index=object_name(names,s,strlen(s),1);
            if (index<0) return -1;
            names->names[index].defined=1;names->names[index].strong=1;continue;
        }
        char *arguments=s;
        while (*arguments && !whitespace((unsigned char)*arguments)) ++arguments;
        if (*arguments) *arguments++=0;
        arguments=trim(arguments);
        if (!strcmp(s,".weakref")) return -1;
        if (!strcmp(s,".pushsection")) { if (++depth>16) return -1; }
        if (!strcmp(s,".popsection")) { if (!depth) return -1;--depth; }
        int weak=!strcmp(s,".weak");
        int external=weak || !strcmp(s,".global") || !strcmp(s,".globl");
        int local=!strcmp(s,".local");
        int common=!strcmp(s,".comm");
        int definition=common || !strcmp(s,".set") || !strcmp(s,".equ");
        if (!external && !local && !definition) continue;
        for (;;) {
            char *comma=strchr(arguments,',');
            if (comma) *comma=0;
            char *name=trim(arguments);
            int index=object_name(names,name,strlen(name),1);
            if (index<0) return -1;
            names->names[index].external|=external;
            names->names[index].weak|=weak;
            names->names[index].local|=local;
            names->names[index].defined|=definition;
            names->names[index].common|=common;
            names->names[index].strong|=definition && !common;
            if (definition) {
                if (!comma) return -1;
                if (common) {
                    char *alignment=strchr(comma+1,',');uint32_t size,align=4;
                    if (alignment) { *alignment++=0;alignment=trim(alignment); }
                    char *amount=trim(comma+1);
                    if (strchr(amount,'-') || integer(amount,&size) ||
                        (alignment && (strchr(alignment,'-') || integer(alignment,&align))) ||
                        !align || (align&(align-1))) return -1;
                    if (!names->names[index].common_size) names->names[index].common_size=size;
                    if (align>names->names[index].common_alignment) names->names[index].common_alignment=align;
                }
                break;
            }
            if (!comma) break;
            arguments=trim(comma+1);
        }
    }
    if (depth || object_references(names,object,buffer)) return -1;
    for (unsigned i=0;i<names->count;++i) {
        if (names->names[i].local && names->names[i].external) return -1;
        if (names->names[i].common && names->names[i].strong) return -1;
        if (names->names[i].common && names->names[i].weak) return -1;
        if (names->names[i].common && !names->names[i].local) names->names[i].external=1;
        if (names->names[i].referenced && !names->names[i].defined && !names->names[i].local) names->names[i].external=1;
        if ((names->names[i].defined || names->names[i].local) && !names->names[i].external && strlen(names->names[i].name)+7>=64) return -1;
    }
    return 0;
}
static int object_append(char *output, size_t *used, const char *s, size_t n)
{
    if (n>SIZE_MAX-*used) return -1;
    if (output) memcpy(output+*used,s,n);
    *used+=n;return 0;
}
static int object_winner(struct object_names *units, unsigned count, const char *name,
                         unsigned *rank, int *strong_reference)
{
    int winner=-1;*rank=0;*strong_reference=0;
    for (unsigned u=0;u<count;++u) for (unsigned i=0;i<units[u].count;++i) {
        if (!units[u].names[i].external || strcmp(name,units[u].names[i].name)) continue;
        if (!units[u].names[i].weak) *strong_reference=1;
        unsigned priority=units[u].names[i].strong ? (units[u].names[i].weak ? 1u : 3u) :
                          units[u].names[i].common ? 2u : 0u;
        if (priority==3 && *rank==3) return -2;
        if (priority>*rank) { *rank=priority;winner=(int)u; }
    }
    return winner;
}
static int object_decimal(char *, size_t *, uint32_t);
static int object_numeric_name(char *output, size_t *used, unsigned unit, char tag, size_t offset)
{
    char prefix[]=".L.__cA0.N";prefix[6]=tag;
    prefix[7]="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"[unit];
    if (offset>UINT32_MAX) return -1;
    return object_append(output,used,prefix,10) || object_decimal(output,used,(uint32_t)offset) ? -1 : 0;
}
static int object_rewrite(const struct cs_copy_object *object, struct object_names *units, unsigned count,
                          unsigned unit, char tag, char *output, size_t *used, char *buffer)
{
    struct object_names *names=&units[unit];
    size_t offset=0;
    if (object_append(output,used,".text\n",6)) return -1;
    while (offset<object->size) {
        size_t statement=offset;
        if (object_line(object,&offset,buffer)) return -1;
        char *line=trim(buffer);
        if (!strncmp(line,".weak",5) && whitespace((unsigned char)line[5])) continue;
        size_t length=strlen(line);
        int definition=length && line[length-1]==':';
        const char *number_end;uint32_t number;
        if (definition && !decimal_label(line,&number_end,&number)) {
            while (whitespace((unsigned char)*number_end)) ++number_end;
            if (*number_end==':' && !number_end[1]) {
                if (object_numeric_name(output,used,unit,tag,statement) ||
                    object_append(output,used,":\n",2)) return -1;
                continue;
            }
        }
        int alias=(!strncmp(line,".set",4) || !strncmp(line,".equ",4)) && whitespace((unsigned char)line[4]);
        if (!strncmp(line,".comm",5) && whitespace((unsigned char)line[5])) {
            const char *name=line+5;
            while (whitespace((unsigned char)*name)) ++name;
            const char *end=name;
            while (name_char((unsigned char)*end)) ++end;
            int index=object_name(names,name,(size_t)(end-name),0);
            if (index<0) return -1;
            if (names->names[index].external) continue;
        }
        const char *s=buffer;
        int quoted=0;
        while (*s) {
            if (*s=='"') quoted=!quoted;
            if (quoted && *s=='\\' && s[1]) {
                if (object_append(output,used,s,2)) return -1;
                s+=2;continue;
            }
            if (!quoted && (s==buffer || !name_char((unsigned char)s[-1])) &&
                !decimal_label(s,&number_end,&number) && (*number_end=='b' || *number_end=='f') &&
                !name_char((unsigned char)number_end[1])) {
                size_t target;
                if (numeric_target(object->assembly,object->size,statement,number,*number_end=='f',&target) ||
                    object_numeric_name(output,used,unit,tag,target)) return -1;
                s=number_end+1;continue;
            }
            if (!quoted && name_start((unsigned char)*s) && (s==buffer || !name_char((unsigned char)s[-1]))) {
                const char *end=s+1;
                while (name_char((unsigned char)*end)) ++end;
                int index=object_name(names,s,(size_t)(end-s),0);
                int discarded=0;
                if (index>=0 && names->names[index].weak && names->names[index].strong && (definition || alias)) {
                    unsigned rank;int referenced;
                    int winner=object_winner(units,count,names->names[index].name,&rank,&referenced);
                    if (winner==-2) return -1;
                    discarded=winner!=(int)unit;
                }
                if (index>=0 && (((names->names[index].defined || names->names[index].local) && !names->names[index].external) || discarded)) {
                    char prefix[]=".__cA0.";prefix[4]=tag;
                    prefix[5]="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"[unit];
                    if (!strncmp(names->names[index].name,".L",2)) {
                        if (object_append(output,used,".L",2)) return -1;
                        s+=2;
                    }
                    if (object_append(output,used,prefix,7)) return -1;
                }
                if (object_append(output,used,s,(size_t)(end-s))) return -1;
                s=end;
            } else {
                if (object_append(output,used,s++,1)) return -1;
            }
        }
        if (quoted || object_append(output,used,"\n",1)) return -1;
    }
    return 0;
}
static int object_decimal(char *output, size_t *used, uint32_t value)
{
    char digits[10];unsigned count=0;
    do { digits[count++]=(char)('0'+value%10);value/=10; } while (value);
    while (count) if (object_append(output,used,&digits[--count],1)) return -1;
    return 0;
}
static int object_commons(struct object_names *units, unsigned count, char *output, size_t *used)
{
    for (unsigned u=0;u<count;++u) for (unsigned i=0;i<units[u].count;++i) {
        if (!units[u].names[i].external || !units[u].names[i].common) continue;
        const char *name=units[u].names[i].name;
        uint32_t size=0,alignment=0;int strong=0,earlier=0;
        for (unsigned v=0;v<count;++v) for (unsigned j=0;j<units[v].count;++j) {
            if (!units[v].names[j].external || strcmp(name,units[v].names[j].name)) continue;
            strong|=units[v].names[j].strong && !units[v].names[j].weak;
            if (!units[v].names[j].common) continue;
            earlier|=v<u || (v==u && j<i);
            if (units[v].names[j].common_size>size) size=units[v].names[j].common_size;
            if (units[v].names[j].common_alignment>alignment) alignment=units[v].names[j].common_alignment;
        }
        if (strong || earlier) continue;
        if (object_append(output,used,".comm ",6) || object_append(output,used,name,strlen(name)) ||
            object_append(output,used,",",1) || object_decimal(output,used,size) ||
            object_append(output,used,",",1) || object_decimal(output,used,alignment) ||
            object_append(output,used,"\n",1)) return -1;
    }
    return 0;
}
static int object_weak_imports(struct object_names *units, unsigned count, char *output, size_t *used)
{
    for (unsigned u=0;u<count;++u) for (unsigned i=0;i<units[u].count;++i) {
        if (!units[u].names[i].external) continue;
        unsigned rank;int strong_reference;
        const char *name=units[u].names[i].name;
        int winner=object_winner(units,count,name,&rank,&strong_reference);
        if (winner==-2) return -1;
        if (rank || strong_reference || !units[u].names[i].weak) continue;
        int earlier=0;
        for (unsigned v=0;v<u;++v) {
            int index=object_name(&units[v],name,strlen(name),0);
            if (index>=0 && units[v].names[index].external && units[v].names[index].weak) earlier=1;
        }
        if (!earlier && (object_append(output,used,".weak ",6) ||
            object_append(output,used,name,strlen(name)) || object_append(output,used,"\n",1))) return -1;
    }
    return 0;
}
int cs_copy_link_objects(unsigned char *data, size_t bytes, unsigned address_bits,
                        const struct cs_copy_object *objects, unsigned count,
                        char *assembly, size_t capacity,
                        const char *entry, const uint32_t *arguments, unsigned argc,
                        struct cs_copy_link_error *error)
{
    return cs_copy_link_objects_memory(data,bytes,address_bits,8192,objects,count,
                                       assembly,capacity,entry,arguments,argc,error);
}

static int link_objects(unsigned char *data, size_t bytes, unsigned address_bits,
                        uint32_t memory_bytes, const struct cs_copy_object *objects, unsigned count,
                        char *assembly, size_t capacity, int allocate,
                        const char *entry, const uint32_t *arguments, unsigned argc,
                        struct cs_copy_link_error *error)
{
    char *buffer=NULL, *owned=NULL;
    struct object_names *names=NULL;
    const char *message="invalid separate link input";
    if (!objects || !count || count>CS_COPY_MAX_OBJECTS) goto fail;
    if (count==1) return cs_copy_link_program_memory(data,bytes,address_bits,memory_bytes,objects[0].assembly,
                                            objects[0].size,entry,arguments,argc,error);
    size_t buffer_capacity=1;
    for (unsigned i=0;i<count;++i) {
        if (!objects[i].assembly || memchr(objects[i].assembly,0,objects[i].size)) goto fail;
        size_t n=statement_capacity(objects[i].assembly,objects[i].size);
        if (!n) goto fail;
        if (n>buffer_capacity) buffer_capacity=n;
    }
    message="out of memory for assembly operator";
    if (!(buffer=malloc(buffer_capacity))) goto fail;
    message="out of memory for separate link symbols";
    if (sizeof(*names)>SIZE_MAX/count) goto fail;
    if (!(names=malloc(count*sizeof(*names)))) goto fail;
    memset(names,0,count*sizeof(*names));
    size_t needed=0;
    unsigned char occupied[256]={0};
    message="unsupported binding or invalid object assembly";
    for (unsigned i=0;i<count;++i) {
        if (!objects[i].assembly || memchr(objects[i].assembly,0,objects[i].size) ||
            object_scan(&names[i],&objects[i],buffer)) goto fail;
        for (size_t j=0;j<objects[i].size && objects[i].size-j>=5;++j)
            if (!memcmp(objects[i].assembly+j,".__c",4)) occupied[(unsigned char)objects[i].assembly[j+4]]=1;
    }
    const char *tags="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
    unsigned tag=0;
    while (tags[tag] && occupied[(unsigned char)tags[tag]]) ++tag;
    if (!tags[tag]) goto fail;
    for (unsigned i=0;i<count;++i)
        if (object_rewrite(&objects[i],names,count,i,tags[tag],NULL,&needed,buffer)) goto fail;
    if (object_commons(names,count,NULL,&needed) || object_weak_imports(names,count,NULL,&needed)) goto fail;
    if (allocate) {
        message="out of memory for separate link text";
        if (needed==SIZE_MAX || !(owned=malloc(needed+1))) goto fail;
        assembly=owned;capacity=needed+1;
    }
    message="separate link scratch buffer too small";
    if (!assembly || needed>=capacity) goto fail;
    size_t used=0;
    for (unsigned i=0;i<count;++i)
        if (object_rewrite(&objects[i],names,count,i,tags[tag],assembly,&used,buffer)) goto fail;
    if (object_commons(names,count,assembly,&used) || object_weak_imports(names,count,assembly,&used)) goto fail;
    assembly[used]=0;
    free(buffer);
    free(names);
    int result=cs_copy_link_program_memory(data,bytes,address_bits,memory_bytes,assembly,used,entry,arguments,argc,error);
    free(owned);
    return result;
fail:
    free(names);
    free(owned);
    free(buffer);
    if (error) *error=(struct cs_copy_link_error){0,message};
    return -1;
}

int cs_copy_link_objects_memory(unsigned char *data, size_t bytes, unsigned address_bits,
                        uint32_t memory_bytes, const struct cs_copy_object *objects, unsigned count,
                        char *assembly, size_t capacity,
                        const char *entry, const uint32_t *arguments, unsigned argc,
                        struct cs_copy_link_error *error)
{
    return link_objects(data,bytes,address_bits,memory_bytes,objects,count,assembly,capacity,0,
                        entry,arguments,argc,error);
}

int cs_copy_link_objects_alloc(unsigned char *data, size_t bytes, unsigned address_bits,
                        uint32_t memory_bytes, const struct cs_copy_object *objects, unsigned count,
                        const char *entry, const uint32_t *arguments, unsigned argc,
                        struct cs_copy_link_error *error)
{
    return link_objects(data,bytes,address_bits,memory_bytes,objects,count,NULL,0,1,
                        entry,arguments,argc,error);
}

static int archive_decimal(const char *s, size_t bytes, size_t *value)
{
    size_t n=0,i=0;
    while (i<bytes && s[i]>='0' && s[i]<='9') {
        unsigned digit=(unsigned)(s[i++]-'0');
        if (n>(SIZE_MAX-digit)/10) return -1;
        n=n*10+digit;
    }
    if (!i) return -1;
    while (i<bytes) if (s[i++]!=' ') return -1;
    *value=n;return 0;
}

static int archive_members(const char *archive, size_t size,
                            struct cs_copy_object *members, unsigned *count, unsigned capacity)
{
    if (!archive || size<8 || memcmp(archive,"!<arch>\n",8)) return -1;
    size_t at=8;*count=0;
    while (at<size) {
        if (size-at<60) return -1;
        const char *header=archive+at;
        size_t bytes;
        if (memcmp(header+58,"`\n",2) || archive_decimal(header+48,10,&bytes)) return -1;
        at+=60;
        if (bytes>size-at) return -1;
        size_t name_size=16;
        while (name_size && header[name_size-1]==' ') --name_size;
        if (!name_size) return -1;
        int metadata=(name_size==1 && header[0]=='/') ||
                     (name_size==2 && !memcmp(header,"//",2)) ||
                     (name_size==7 && !memcmp(header,"/SYM64/",7));
        size_t filename=0;
        if (name_size>3 && !memcmp(header,"#1/",3)) {
            if (archive_decimal(header+3,name_size-3,&filename) || filename>bytes) return -1;
            /* BSD symbol index, with its name embedded before the data. */
            if (filename>=9 && !memcmp(archive+at,"__.SYMDEF",9)) metadata=1;
        } else if (name_size>=9 && !memcmp(header,"__.SYMDEF",9)) metadata=1;
        if (!metadata) {
            if (*count==capacity) return -1;
            members[(*count)++]=(struct cs_copy_object){archive+at+filename,bytes-filename};
        }
        at+=bytes;
        if (bytes&1) {
            if (at==size || archive[at++]!='\n') return -1;
        }
    }
    return 0;
}

/* Closure needs only the global definitions and strong references. Preserve
   per-unit binding details for the final rewrite, after selection is complete. */
static int archive_requirements(struct object_names *required, struct object_names *unit,
                                 const char *entry, int first)
{
    for (unsigned i=0;i<unit->count;++i) {
        int defined=unit->names[i].defined;
        int referenced=unit->names[i].referenced && !unit->names[i].weak;
        int root_entry=first && defined && !strcmp(unit->names[i].name,entry);
        if (!root_entry && (!unit->names[i].external || (!defined && !referenced))) continue;
        int j=object_name(required,unit->names[i].name,strlen(unit->names[i].name),1);
        if (j<0) return -1;
        required->names[j].defined|=defined;
        required->names[j].referenced|=referenced;
    }
    return 0;
}

static int archive_needed(struct object_names *required, struct object_names *candidate)
{
    for (unsigned i=0;i<candidate->count;++i) {
        if (!candidate->names[i].external || !candidate->names[i].defined) continue;
        int j=object_name(required,candidate->names[i].name,strlen(candidate->names[i].name),0);
        if (j>=0 && required->names[j].referenced && !required->names[j].defined) return 1;
    }
    return 0;
}

int cs_copy_link_archives_alloc(unsigned char *data, size_t bytes, unsigned address_bits,
                        uint32_t memory_bytes, const struct cs_copy_object *objects, unsigned count,
                        const struct cs_copy_archive *archives, unsigned archive_count,
                        const char *entry, const uint32_t *arguments, unsigned argc,
                        struct cs_copy_link_error *error)
{
    const char *message="invalid copy archive input";
    struct cs_copy_object members[CS_COPY_MAX_ARCHIVE_MEMBERS],selected[CS_COPY_MAX_OBJECTS];unsigned member_count=0;
    struct object_names *names=NULL;
    char *buffer=NULL;
    if (!objects || !count || count>CS_COPY_MAX_OBJECTS || !entry || !*entry ||
        !archives || !archive_count || archive_count>CS_COPY_MAX_ARCHIVE_MEMBERS) goto fail;
    for (unsigned i=0;i<archive_count;++i) {
        unsigned added;
        if (archive_members(archives[i].data,archives[i].size,members+member_count,&added,
                            CS_COPY_MAX_ARCHIVE_MEMBERS-member_count)) goto fail;
        member_count+=added;
    }
    size_t capacity=1;
    for (unsigned i=0;i<count+member_count;++i) {
        const struct cs_copy_object *object=i<count ? &objects[i] : &members[i-count];
        if (!object->assembly || memchr(object->assembly,0,object->size)) goto fail;
        size_t n=statement_capacity(object->assembly,object->size);
        if (!n) goto fail;
        if (n>capacity) capacity=n;
    }
    message="out of memory for archive symbols";
    names=malloc(2*sizeof(*names));
    buffer=malloc(capacity);
    if (!names || !buffer) goto fail;
    memset(names,0,2*sizeof(*names));
    message="unsupported binding or invalid archive assembly";
    int entry_index=object_name(&names[0],entry,strlen(entry),1);
    if (entry_index<0) goto fail;
    names[0].names[entry_index].referenced=1;
    for (unsigned i=0;i<count;++i) {
        selected[i]=objects[i];
        memset(&names[1],0,sizeof(*names));
        if (object_scan(&names[1],&objects[i],buffer) ||
            archive_requirements(&names[0],&names[1],entry,i==0)) goto fail;
    }
    unsigned char extracted[CS_COPY_MAX_ARCHIVE_MEMBERS]={0};
    int changed;
    do {
        changed=0;
        for (unsigned m=0;m<member_count;++m) {
            if (extracted[m]) continue;
            memset(&names[1],0,sizeof(*names));
            if (object_scan(&names[1],&members[m],buffer)) goto fail;
            if (!archive_needed(&names[0],&names[1])) continue;
            message="too many selected copy archive units";
            if (count==CS_COPY_MAX_OBJECTS) goto fail;
            selected[count++]=members[m];
            if (archive_requirements(&names[0],&names[1],entry,0)) goto fail;
            extracted[m]=1;changed=1;
            message="unsupported binding or invalid archive assembly";
        }
    } while (changed);
    free(buffer);free(names);
    return cs_copy_link_objects_alloc(data,bytes,address_bits,memory_bytes,selected,count,
                                     entry,arguments,argc,error);
fail:
    free(buffer);free(names);
    if (error) *error=(struct cs_copy_link_error){0,message};
    return -1;
}

int cs_copy_link_archive_alloc(unsigned char *data, size_t bytes, unsigned address_bits,
                        uint32_t memory_bytes, const struct cs_copy_object *objects, unsigned count,
                        const char *archive, size_t archive_size,
                        const char *entry, const uint32_t *arguments, unsigned argc,
                        struct cs_copy_link_error *error)
{
    const struct cs_copy_archive input={archive,archive_size};
    return cs_copy_link_archives_alloc(data,bytes,address_bits,memory_bytes,objects,count,
                                      &input,1,entry,arguments,argc,error);
}
