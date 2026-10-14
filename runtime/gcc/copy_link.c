#include "copy_link.h"
#include "copy_emit.h"
#include <string.h>

enum { REG_BASE=32768, CONSTANT_BASE=33344, ADD_TABLE=33792,
       SUB_TABLE=33808, AND_TABLE=33824, OR_TABLE=33828, XOR_TABLE=33832,
       TEMPORARY=33840, CARRY=33842, OUTPUT=34000, STATUS=34100, ZERO_LAYER=36352 };
struct context {
    struct cs_copy_program program;
    uint32_t constants[12];
    unsigned constant_count;
    struct { char name[64]; uint32_t address; int defined; } labels[32];
    struct { uint32_t layer; int label; size_t line; } jumps[64];
    unsigned label_count, jump_count;
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
    uint32_t destination, source;
    if (reg(trim(operands),&destination)) return "invalid destination register";
    char *argument=trim(comma);
    int rc;
    if (!strcmp(s,"copy.ldi.l") || !strcmp(s,"copy.inc") || !strcmp(s,"copy.dec")) {
        uint32_t value;
        if (integer(argument,&value)) return "invalid 32-bit integer";
        if (constant(ctx,value,&source)) return "constant capacity exceeded";
        if (!strcmp(s,"copy.ldi.l")) rc=cs_copy_program_emit(&ctx->program,32,destination,source);
        else if (!strcmp(s,"copy.inc")) rc=cs_copy_program_add32(&ctx->program,destination,destination,source,ADD_TABLE,TEMPORARY,CARRY);
        else rc=cs_copy_program_sub32(&ctx->program,destination,destination,source,SUB_TABLE,TEMPORARY,CARRY);
    } else {
        if (reg(argument,&source)) return "invalid source register";
        if (!strcmp(s,"copy.mov")) rc=cs_copy_program_emit(&ctx->program,32,destination,source);
        else if (!strcmp(s,"copy.add")) rc=cs_copy_program_add32(&ctx->program,destination,destination,source,ADD_TABLE,TEMPORARY,CARRY);
        else if (!strcmp(s,"copy.sub")) rc=cs_copy_program_sub32(&ctx->program,destination,destination,source,SUB_TABLE,TEMPORARY,CARRY);
        else if (!strcmp(s,"copy.and")) rc=cs_copy_program_bits32(&ctx->program,CS_COPY_AND,destination,destination,source,AND_TABLE);
        else if (!strcmp(s,"copy.or")) rc=cs_copy_program_bits32(&ctx->program,CS_COPY_OR,destination,destination,source,OR_TABLE);
        else if (!strcmp(s,"copy.xor")) rc=cs_copy_program_bits32(&ctx->program,CS_COPY_XOR,destination,destination,source,XOR_TABLE);
        else return "unsupported operation";
    }
    return rc ? "copy image capacity exceeded" : NULL;
}

int cs_copy_link_leaf(unsigned char *data, size_t bytes, unsigned address_bits,
                       const char *assembly, size_t size, const char *entry,
                       const uint32_t *arguments, unsigned argc,
                       struct cs_copy_link_error *error)
{
    struct context ctx;
    const char *message="invalid link input";
    size_t line=0, offset=0;
    int entered=0, returned=0, terminated=0;
    if (!data || bytes<32768 || bytes>UINT32_MAX/8 || !assembly || !entry || !*entry ||
        argc>6 || (argc && !arguments) || memchr(assembly,0,size)) goto fail;
    memset(data,0,bytes);
    memset(&ctx,0,sizeof(ctx));
    if (cs_copy_program_init(&ctx.program,data,bytes,address_bits,65536,(uint32_t)(bytes*8))) goto fail;
    for (unsigned i=0;i<argc;++i)
        if (cs_copy_constant(&ctx.program.image,REG_BASE+32*(i+2),32,arguments[i])) goto fail;
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
            if ((!entered && strcmp(s,entry)) || (entered && strncmp(s,".L",2))) goto fail;
            int index=label(&ctx,s);
            message="invalid or duplicate copy label";
            if (index<0 || ctx.labels[index].defined) goto fail;
            if (ctx.program.image.slot!=3 && cs_copy_program_next(&ctx.program)) {
                message="copy image capacity exceeded"; goto fail;
            }
            ctx.labels[index].address=ctx.program.image.layer;
            ctx.labels[index].defined=1;
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
            if (jump(&ctx,-2,line)) goto fail;
            returned=1; terminated=1; continue;
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
    message="copy image capacity exceeded";
    if (cs_copy_program_next(&ctx.program)) goto fail;
    uint32_t report=ctx.program.image.layer;
    for (unsigned i=0;i<ctx.jump_count;++i) {
        int index=ctx.jumps[i].label;
        if (index>=0 && !ctx.labels[index].defined) {
            line=ctx.jumps[i].line; message="undefined copy label"; goto fail;
        }
        uint32_t target=index==-2 ? report : ctx.labels[index].address;
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
