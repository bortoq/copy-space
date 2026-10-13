#include <stdint.h>

typedef struct { uint64_t bits; int unsign; } cc_pp_value;
typedef struct { cc_pp_reader reader; cc_pp_token token; int failed; unsigned depth; } cc_pp_eval;
typedef struct { int parent, taken, active, saw_else; } cc_pp_group;
static cc_pp_group cc_pp_groups[64];
static unsigned cc_pp_group_count, cc_pp_group_floor;

static void cc_pp_eval_next(cc_pp_eval *e)
{
    e->token=cc_pp_next(&e->reader);
    if (e->reader.failed) e->failed=1;
}
static unsigned cc_pp_hex(unsigned char c)
{
    if (cc_pp_digit(c)) return c-'0';
    if (c >= 'a' && c <= 'f') return c-'a'+10;
    if (c >= 'A' && c <= 'F') return c-'A'+10;
    return 99;
}
static cc_pp_value cc_pp_constant(cc_pp_eval *e)
{
    cc_pp_token t=e->token;
    cc_pp_value v={0,0};
    if (t.kind == CC_PP_IDENT) {
        if (cc_pp_query_kind(t)) e->failed=1;
        return v;
    }
    if (t.kind == CC_PP_LITERAL) {
        unsigned at=0, count=0;
        int wide=t.text[0] != '\'';
        if (wide) ++at;
        if (at >= t.size || t.text[at++] != '\'') { e->failed=1; return v; }
        while (at+1 < t.size) {
            unsigned c=t.text[at++];
            if (c == '\\') {
                c=t.text[at++];
                if (c >= '0' && c <= '7') {
                    unsigned n=1, value=c-'0';
                    while (n<3 && at+1<t.size && t.text[at]>='0' && t.text[at]<='7') {
                        value=(value<<3)+(t.text[at++]-'0'); ++n;
                    }
                    c=value;
                } else if (c == 'x') {
                    unsigned n=0, value=0;
                    while (at+1<t.size && cc_pp_hex(t.text[at])<16) {
                        value=(value<<4)+cc_pp_hex(t.text[at++]); ++n;
                    }
                    if (!n) e->failed=1;
                    c=value;
                } else {
                    if (c=='a') c=7; else if (c=='b') c=8; else if (c=='e') c=27;
                    else if (c=='f') c=12; else if (c=='n') c=10; else if (c=='r') c=13;
                    else if (c=='t') c=9; else if (c=='v') c=11;
                    else if (c=='u' || c=='U') { e->failed=1; return v; }
                }
            }
            v.bits=wide ? c : (v.bits<<8)|(c&255); ++count;
        }
        if (!count) e->failed=1;
        if (!wide && count == 1) v.bits=(uint64_t)(int64_t)(int8_t)v.bits;
        else v.bits=(uint64_t)(int64_t)(int32_t)v.bits;
        return v;
    }
    if (t.kind != CC_PP_NUMBER) { e->failed=1; return v; }
    unsigned radix=10, at=0, digits=0;
    if (t.text[0]=='0') {
        radix=8;
        if (t.size>1 && (t.text[1]=='x' || t.text[1]=='X')) { radix=16; at=2; }
        else if (t.size>1 && (t.text[1]=='b' || t.text[1]=='B')) { radix=2; at=2; }
    }
    while (at<t.size && cc_pp_hex(t.text[at])<radix) {
        unsigned digit=cc_pp_hex(t.text[at++]);
        if (v.bits>(UINT64_MAX-digit)/radix) { e->failed=1; return v; }
        v.bits=v.bits*radix+digit; ++digits;
    }
    if (!digits) e->failed=1;
    unsigned longs=0; unsigned char long_case=0;
    while (at<t.size) {
        unsigned char c=t.text[at++];
        if (c=='u' || c=='U') {
            if (v.unsign) e->failed=1;
            v.unsign=1;
        } else if (c=='l' || c=='L') {
            if (longs && (longs!=1 || c!=long_case || t.text[at-2]!=c)) e->failed=1;
            long_case=c; ++longs;
        } else e->failed=1;
    }
    if (v.bits>>63) v.unsign=1;
    return v;
}
static int cc_pp_precedence(cc_pp_token t)
{
    static const char *const ops[]={",","?","||","&&","|","^","&","==","!=",
        "<","<=",">",">=","<<",">>","+","-","*","/","%",0};
    static const unsigned levels[]={1,2,3,4,5,6,7,8,8,9,9,9,9,10,10,11,11,12,12,12};
    for (unsigned i=0; ops[i]; ++i) if (cc_pp_is(t,ops[i])) return (int)levels[i];
    return 0;
}
static cc_pp_value cc_pp_evaluate(cc_pp_eval *e, unsigned minimum, int run);
static cc_pp_value cc_pp_unary(cc_pp_eval *e, int run)
{
    cc_pp_token t=e->token;
    cc_pp_value v={0,0};
    if (++e->depth>64) { e->failed=1; return v; }
    if (cc_pp_is(t,"(")) {
        cc_pp_eval_next(e); v=cc_pp_evaluate(e,1,run);
        if (!cc_pp_is(e->token,")")) e->failed=1; else cc_pp_eval_next(e);
    } else if (cc_pp_is(t,"+") || cc_pp_is(t,"-") || cc_pp_is(t,"!") || cc_pp_is(t,"~")) {
        cc_pp_eval_next(e); v=cc_pp_unary(e,run);
        if (cc_pp_is(t,"!")) { v.bits=run && !v.bits; v.unsign=0; }
        else if (run && cc_pp_is(t,"-")) v.bits=0-v.bits;
        else if (run && cc_pp_is(t,"~")) v.bits=~v.bits;
    } else {
        v=cc_pp_constant(e); cc_pp_eval_next(e);
        if (!run) v.bits=0;
    }
    --e->depth;
    return v;
}
static cc_pp_value cc_pp_binary(cc_pp_eval *e, cc_pp_token op, cc_pp_value a, cc_pp_value b, int run)
{
    cc_pp_value v={0,a.unsign|b.unsign};
    if (cc_pp_is(op,",")) return b;
    if (cc_pp_is(op,"<<") || cc_pp_is(op,">>")) v.unsign=a.unsign;
    int boolean=cc_pp_precedence(op)==8 || cc_pp_precedence(op)==9 || cc_pp_is(op,"&&") || cc_pp_is(op,"||");
    if (boolean) v.unsign=0;
    if (!run) return v;
    if (cc_pp_is(op,"+")) v.bits=a.bits+b.bits;
    else if (cc_pp_is(op,"-")) v.bits=a.bits-b.bits;
    else if (cc_pp_is(op,"*")) v.bits=a.bits*b.bits;
    else if (cc_pp_is(op,"&")) v.bits=a.bits&b.bits;
    else if (cc_pp_is(op,"|")) v.bits=a.bits|b.bits;
    else if (cc_pp_is(op,"^")) v.bits=a.bits^b.bits;
    else if (cc_pp_is(op,"&&")) v.bits=!!a.bits && !!b.bits;
    else if (cc_pp_is(op,"||")) v.bits=!!a.bits || !!b.bits;
    else if (cc_pp_is(op,"==")) v.bits=a.bits==b.bits;
    else if (cc_pp_is(op,"!=")) v.bits=a.bits!=b.bits;
    else if (cc_pp_is(op,"<<") || cc_pp_is(op,">>")) {
        if (b.bits>=64) e->failed=1;
        else if (cc_pp_is(op,"<<")) v.bits=a.bits<<b.bits;
        else if (a.unsign) v.bits=a.bits>>b.bits;
        else v.bits=(uint64_t)((int64_t)a.bits>>b.bits);
    } else if (cc_pp_is(op,"/") || cc_pp_is(op,"%")) {
        if (!b.bits || (!(a.unsign|b.unsign) && a.bits==((uint64_t)1<<63) && b.bits==UINT64_MAX)) e->failed=1;
        else if (a.unsign|b.unsign) v.bits=cc_pp_is(op,"/") ? a.bits/b.bits : a.bits%b.bits;
        else v.bits=(uint64_t)(cc_pp_is(op,"/") ? (int64_t)a.bits/(int64_t)b.bits : (int64_t)a.bits%(int64_t)b.bits);
    } else {
        int less=(a.unsign|b.unsign) ? a.bits<b.bits : (int64_t)a.bits<(int64_t)b.bits;
        if (cc_pp_is(op,"<")) v.bits=less;
        else if (cc_pp_is(op,"<=")) v.bits=less || a.bits==b.bits;
        else if (cc_pp_is(op,">")) v.bits=!less && a.bits!=b.bits;
        else if (cc_pp_is(op,">=")) v.bits=!less;
        else e->failed=1;
    }
    return v;
}
static cc_pp_value cc_pp_evaluate(cc_pp_eval *e, unsigned minimum, int run)
{
    cc_pp_value v={0,0};
    if (++e->depth>64) { e->failed=1; return v; }
    v=cc_pp_unary(e,run);
    while (!e->failed) {
        unsigned priority=(unsigned)cc_pp_precedence(e->token);
        if (priority<minimum) break;
        cc_pp_token op=e->token; cc_pp_eval_next(e);
        if (cc_pp_is(op,"?")) {
            int selected=!!v.bits;
            if (cc_pp_is(e->token,":")) { e->failed=1; break; }
            cc_pp_value a=cc_pp_evaluate(e,1,run && selected);
            if (!cc_pp_is(e->token,":")) { e->failed=1; break; }
            cc_pp_eval_next(e);
            cc_pp_value b=cc_pp_evaluate(e,priority,run && !selected);
            v.bits=selected ? a.bits : b.bits; v.unsign=a.unsign|b.unsign;
        } else {
            int right_run=run;
            if (cc_pp_is(op,"&&") && !v.bits) right_run=0;
            if (cc_pp_is(op,"||") && v.bits) right_run=0;
            cc_pp_value b=cc_pp_evaluate(e,priority+1,right_run);
            v=cc_pp_binary(e,op,v,b,run);
        }
    }
    --e->depth;
    return v;
}
static int cc_pp_skip_line(cc_pp_reader *reader)
{
    int previous=cc_pp_skipping;
    cc_pp_skipping=1;
    cc_pp_token t;
    do { t=cc_pp_next(reader); } while (t.kind && t.kind!='\n' && !reader->failed);
    cc_pp_skipping=previous;
    return !reader->failed;
}
static int cc_pp_condition_line_run(cc_pp_reader *reader, int run, int *truth)
{
    *truth=0;
    if (!run) return cc_pp_skip_line(reader);
    cc_pp_skipping=0;
    unsigned start=cc_pp_output_count;
    unsigned head=0, tail=0;
    unsigned state=0;
    cc_pp_token t=cc_pp_condition_token(reader,&state);
    while (t.kind && t.kind!='\n' && !reader->failed) {
        if (cc_pp_is(t,"defined")) {
            t=cc_pp_next(reader); int parens=cc_pp_is(t,"(");
            if (parens) t=cc_pp_next(reader);
            if (t.kind!=CC_PP_IDENT) return 0;
            int exists=cc_pp_is_defined(t);
            if (parens && !cc_pp_is(cc_pp_next(reader),")")) return 0;
            t=(cc_pp_token){(const unsigned char *)(exists ? "1" : "0"),1,CC_PP_NUMBER,0,0};
            state=0;
        }
        unsigned node=cc_pp_node_new(t);
        if (!node) { cc_pp_list_release(head); return 0; }
        if (tail) cc_pp_nodes[tail].next=node; else head=node;
        tail=node;
        t=cc_pp_condition_token(reader,&state);
    }
    if (!cc_pp_flush(head)) return 0;
    cc_pp_eval e={{cc_pp_output+start,cc_pp_output_count-start,0,0},{0,0,0,0,0},0,0};
    cc_pp_eval_next(&e);
    cc_pp_value value=cc_pp_evaluate(&e,1,1);
    cc_pp_output_count=start;
    if (reader->failed || e.failed || e.token.kind) return 0;
    *truth=!!value.bits;
    return 1;
}
static int cc_pp_condition_line(cc_pp_reader *reader, int run, int *truth)
{
    int previous=cc_pp_in_condition;
    cc_pp_in_condition=1;
    int result=cc_pp_condition_line_run(reader,run,truth);
    cc_pp_in_condition=previous;
    return result;
}
static int cc_pp_condition_directive(cc_pp_reader *r, cc_pp_token directive)
{
    int ifdef=cc_pp_is(directive,"ifdef"), ifndef=cc_pp_is(directive,"ifndef");
    int is_if=cc_pp_is(directive,"if"), elif=cc_pp_is(directive,"elif");
    int is_else=cc_pp_is(directive,"else"), endif=cc_pp_is(directive,"endif");
    if (!ifdef && !ifndef && !is_if && !elif && !is_else && !endif) return -1;
    int truth=0;
    if (is_if || ifdef || ifndef) {
        if (cc_pp_group_count==64) return 0;
        if (is_if) { if (!cc_pp_condition_line(r,cc_pp_enabled,&truth)) return 0; }
        else if (cc_pp_enabled) {
            cc_pp_token name=cc_pp_next(r);
            if (name.kind!=CC_PP_IDENT) return 0;
            truth=cc_pp_is_defined(name);
            if (ifndef) truth=!truth;
            cc_pp_token tail=cc_pp_next(r);
            if (tail.kind && tail.kind!='\n') return 0;
        } else if (!cc_pp_skip_line(r)) return 0;
        cc_pp_group group={cc_pp_enabled,truth,cc_pp_enabled && truth,0};
        cc_pp_groups[cc_pp_group_count++]=group; cc_pp_enabled=group.active;
    } else {
        if (cc_pp_group_count == cc_pp_group_floor) return 0;
        cc_pp_group *group=cc_pp_groups+cc_pp_group_count-1;
        if (elif) {
            if (group->saw_else || !cc_pp_condition_line(r,group->parent && !group->taken,&truth)) return 0;
            group->active=group->parent && !group->taken && truth;
            if (group->active) group->taken=1;
            cc_pp_enabled=group->active;
        } else {
            cc_pp_token tail=cc_pp_next(r);
            if (tail.kind && tail.kind!='\n') return 0;
            if (is_else) {
                if (group->saw_else) return 0;
                group->saw_else=1; group->active=group->parent && !group->taken;
                group->taken=1; cc_pp_enabled=group->active;
            } else { cc_pp_enabled=group->parent; --cc_pp_group_count; }
        }
    }
    return !r->failed;
}
