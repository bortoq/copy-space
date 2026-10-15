#include "copy_link.h"
#include "copy_emit.h"
#include <string.h>

enum { REG_BASE=32768, CONSTANT_BASE=33344, ADD_TABLE=33792,
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
       RETURN_FP=34848, RETURN_PC=34880, CALL_TABLE=64128,
       OUTPUT=34000, STATUS=34100, ZERO_LAYER=36352 };
struct context {
    struct cs_copy_program program;
    uint32_t constants[12];
    unsigned constant_count;
    struct { char name[64]; uint32_t address; int defined; } labels[32];
    struct { uint32_t layer, table, fallthrough; int label, inverted; size_t line; } jumps[64];
    unsigned label_count, jump_count;
    int compared;
    uint32_t data_begin;
    int memory_fault;
    int return_handler;
    unsigned call_count;
};

static int label(struct context *ctx, const char *name)
{
    size_t length=strlen(name);
    if (!length || length>=sizeof(ctx->labels[0].name)) return -1;
    for (size_t i=0;i<length;++i) {
        unsigned char c=(unsigned char)name[i];
        if (!(c=='_' || c=='.' || c=='$' || (c>='a' && c<='z') ||
              (c>='A' && c<='Z') || (i && c>='0' && c<='9'))) return -1;
    }
    for (unsigned i=0;i<ctx->label_count;++i)
        if (!strcmp(ctx->labels[i].name,name)) return (int)i;
    if (ctx->label_count==32) return -1;
    unsigned i=ctx->label_count++;
    memcpy(ctx->labels[i].name,name,length+1);
    return (int)i;
}

static int jump(struct context *ctx, int target, size_t line)
{
    if (ctx->jump_count==64) return -1;
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
        if (i==12) return -1;
        ctx->constants[i]=value;
        ++ctx->constant_count;
        if (cs_copy_constant(&ctx->program.image,CONSTANT_BASE+32*i,32,value)) return -1;
    }
    *address=CONSTANT_BASE+32*i;
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
    if (ctx->jump_count==64) return "jump capacity exceeded";
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
    if (ctx->label_count==32 || constant(ctx,0,&zero) || constant(ctx,1,&one)) return -1;
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
    if (ctx->label_count==32) return -1;
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
    if (constant(ctx,8192-width/8,&limit) ||
        cs_copy_program_emit(p,5,MEM_FLAGS,CMP_EQ) || compare32(ctx,MEM_ADDRESS,limit) ||
        cs_copy_program_emit(p,1,MEM_VALID,CMP_LEU) ||
        cs_copy_program_emit(p,5,CMP_EQ,MEM_FLAGS) ||
        conditional_jump(ctx,ctx->memory_fault,MEM_VALID,1,0)) return "copy image capacity exceeded";
    ctx->compared=compared;
    if (cs_copy_constant(&p->image,MEM_BIT_ADDRESS,p->image.address_bits,ctx->data_begin) ||
        cs_copy_program_emit(p,13,MEM_BIT_ADDRESS+3,MEM_ADDRESS)) return "copy image capacity exceeded";
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
        if (integer(address,&absolute) || constant(ctx,absolute,&base)) return "invalid absolute memory address";
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
static const char *call(struct context *ctx, char *name, size_t line)
{
    if (ctx->call_count==32) return "call capacity exceeded";
    int target=label(ctx,name);
    if (target<0) return "invalid function label";
    struct cs_copy_program *p=&ctx->program;
    uint32_t twelve,zero;
    uint32_t continuation=CALL_TABLE+32*ctx->call_count++;
    if (constant(ctx,12,&twelve) || constant(ctx,0,&zero) ||
        cs_copy_program_sub32(p,REG_BASE+32,REG_BASE+32,twelve,SUB_TABLE,TEMPORARY,CARRY) ||
        memory_access(ctx,1,32,REG_BASE,REG_BASE+32,0) ||
        memory_access(ctx,1,32,continuation,REG_BASE+32,4) ||
        memory_access(ctx,1,32,zero,REG_BASE+32,8) ||
        cs_copy_program_emit(p,32,REG_BASE,REG_BASE+32) || jump(ctx,target,line) ||
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
    uint32_t source_field=255*p->image.instruction_bits+p->image.count_bits+p->image.address_bits;
    return cs_copy_program_emit(p,p->image.address_bits,source_field,RETURN_PC) ||
           cs_copy_program_next(p) ? -1 : 0;
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
        if (integer(argument,&value)) return "invalid 32-bit integer";
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

static int link_image(unsigned char *data, size_t bytes, unsigned address_bits,
                       const char *assembly, size_t size, const char *entry,
                       const uint32_t *arguments, unsigned argc,
                       struct cs_copy_link_error *error, int program_mode)
{
    struct context ctx;
    const char *message="invalid link input";
    size_t line=0, offset=0;
    int entered=0, returned=0, terminated=0;
    if (!data || bytes<32768 || bytes>UINT32_MAX/8 || !assembly || !entry || !*entry ||
        argc>6 || (argc && !arguments) || memchr(assembly,0,size)) goto fail;
    memset(data,0,bytes);
    memset(&ctx,0,sizeof(ctx));
    ctx.memory_fault=-1;
    if (cs_copy_program_init(&ctx.program,data,bytes,address_bits,65536,(uint32_t)(bytes*8))) goto fail;
    if (cs_copy_constant(&ctx.program.image,EQ_TABLE,8,144) ||
        cs_copy_constant(&ctx.program.image,LT_TABLE,8,212) ||
        cs_copy_constant(&ctx.program.image,XOR_TABLE,4,6) ||
        cs_copy_constant(&ctx.program.image,AND_TABLE,4,8) ||
        cs_copy_constant(&ctx.program.image,OR_TABLE,4,14)) goto fail;
    if (cs_copy_constant(&ctx.program.image,REG_BASE,32,8192) ||
        cs_copy_constant(&ctx.program.image,REG_BASE+32,32,8192)) goto fail;
    for (unsigned i=0;i<argc;++i)
        if (cs_copy_constant(&ctx.program.image,REG_BASE+32*(i+2),32,arguments[i])) goto fail;
    int entry_label=-1;
    if (program_mode) {
        if (bytes<262144 || ((bytes*8)&65535)) goto fail;
        ctx.data_begin=(uint32_t)(bytes*8)-65536;
        ctx.program.code_limit=ctx.data_begin;
        entry_label=label(&ctx,entry);
        ctx.return_handler=internal_label(&ctx);
        ctx.memory_fault=internal_label(&ctx);
        if (entry_label<0 || ctx.return_handler<0 || ctx.memory_fault<0 ||
            cs_copy_constant(&ctx.program.image,REG_BASE,32,8180) ||
            cs_copy_constant(&ctx.program.image,REG_BASE+32,32,8180) ||
            cs_copy_constant(&ctx.program.image,ctx.data_begin+8180*8,32,8192) ||
            jump(&ctx,entry_label,0)) goto fail;
    }
    while (offset<size) {
        size_t end=offset;
        while (end<size && assembly[end]!='\n') ++end;
        ++line;
        char buffer[256];
        message="assembly line too long";
        if (end-offset>=sizeof(buffer)) goto fail;
        memcpy(buffer,assembly+offset,end-offset); buffer[end-offset]=0;
        offset=end+(end<size);
        char *s=trim(buffer), *comment=strchr(s,'#');
        if (comment) { *comment=0; s=trim(s); }
        if (!*s) continue;
        size_t length=strlen(s);
        if (s[length-1]==':') {
            s[length-1]=0;
            s=trim(s);
            message="only one function and local labels are supported";
            if (!program_mode && ((!entered && strcmp(s,entry)) || (entered && strncmp(s,".L",2)))) goto fail;
            int index=label(&ctx,s);
            message="invalid or duplicate copy label";
            if (index<0 || ctx.labels[index].defined) goto fail;
            if (ctx.program.image.slot!=3 && cs_copy_program_next(&ctx.program)) {
                message="copy image capacity exceeded"; goto fail;
            }
            ctx.labels[index].address=ctx.program.image.layer;
            ctx.labels[index].defined=1;
            if (program_mode && strncmp(s,".L",2)) ctx.compared=0;
            entered=1; terminated=0; continue;
        }
        if (*s=='.') {
            message="unsupported section or directive";
            if (!metadata(s)) goto fail;
            continue;
        }
        message="operation outside leaf body";
        if (!entered || terminated) goto fail;
        if (!strcmp(s,"copy.ret")) {
            message="copy image capacity exceeded";
            if (jump(&ctx,program_mode ? ctx.return_handler : -2,line)) goto fail;
            returned=1; terminated=1; continue;
        }
        if (program_mode && !strncmp(s,"copy.jsra",9) && whitespace((unsigned char)s[9])) {
            message=call(&ctx,trim(s+9),line);
            if (message) goto fail;
            continue;
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
    if (!entered || !returned) goto fail;
    if (program_mode && !ctx.labels[entry_label].defined) goto fail;
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
    if (program_mode && cs_copy_constant(&ctx.program.image,ctx.data_begin+8184*8,32,report)) goto fail;
    for (unsigned i=0;i<ctx.jump_count;++i) {
        int index=ctx.jumps[i].label;
        if (index>=0 && !ctx.labels[index].defined) {
            line=ctx.jumps[i].line; message="undefined copy label"; goto fail;
        }
        uint32_t target=index==-2 ? report : ctx.labels[index].address;
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
    for (unsigned i=0;i<32;++i)
        if (cs_copy_program_emit(&ctx.program,1,OUTPUT+(i/8)*8+7-(i%8),REG_BASE+64+i)) goto fail;
    if (cs_copy_program_next(&ctx.program) || cs_copy_row(&ctx.program.image,2,32,OUTPUT,STATUS) ||
        cs_copy_program_finish(&ctx.program,ZERO_LAYER)) goto fail;
    if (error) *error=(struct cs_copy_link_error){0,NULL};
    return 0;
fail:
    if (error) *error=(struct cs_copy_link_error){line,message};
    return -1;
}

int cs_copy_link_leaf(unsigned char *data, size_t bytes, unsigned address_bits,
                     const char *assembly, size_t size, const char *entry,
                     const uint32_t *arguments, unsigned argc, struct cs_copy_link_error *error)
{
    return link_image(data,bytes,address_bits,assembly,size,entry,arguments,argc,error,0);
}

int cs_copy_link_program(unsigned char *data, size_t bytes, unsigned address_bits,
                        const char *assembly, size_t size, const char *entry,
                        const uint32_t *arguments, unsigned argc, struct cs_copy_link_error *error)
{
    return link_image(data,bytes,address_bits,assembly,size,entry,arguments,argc,error,1);
}
