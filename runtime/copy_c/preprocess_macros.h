#include "preprocess_phase2.h"
/* Guest preprocessing. All pointers refer to guest memory; no file or host
 * service participates in token recognition or macro substitution. */
#ifdef COPY_SPACE_C_COMPILER
static void *cc_pp_allocate(unsigned bytes) { return pfAllocMem((cell_t)bytes); }
static void cc_pp_free(void *memory) { pfFreeMem(memory); }
#else
#include <stdlib.h>
static void *cc_pp_allocate(unsigned bytes) { return malloc(bytes); }
static void cc_pp_free(void *memory) { free(memory); }
#endif
#define CC_PP_IDENT 256
#define CC_PP_NUMBER 257
#define CC_PP_LITERAL 258
#define CC_PP_HEADER 259
#define CC_PP_MACROS 512
#define CC_PP_TOKENS 32768
#define CC_PP_TEXT 262144
#define CC_PP_OUTPUT 1048576
#define CC_PP_PARAMETERS 4096
#define CC_PP_HIDE_SETS 4096
#define CC_PP_HIDE_SLOTS 8192
#define CC_PP_HIDE_WORDS ((CC_PP_MACROS+31)/32)
static unsigned cc_pp_hide_sets[CC_PP_HIDE_SETS][CC_PP_HIDE_WORDS];
static unsigned cc_pp_hide_slots[CC_PP_HIDE_SLOTS], cc_pp_hide_count;
static int cc_pp_hide_intern(const unsigned *bits)
{
    unsigned hash=2166136261u;
    for (unsigned i=0; i<CC_PP_HIDE_WORDS; ++i) hash=(hash^bits[i])*16777619u;
    unsigned slot=hash&(CC_PP_HIDE_SLOTS-1);
    while (cc_pp_hide_slots[slot]) {
        unsigned index=cc_pp_hide_slots[slot]-1, i=0;
        while (i<CC_PP_HIDE_WORDS && cc_pp_hide_sets[index][i] == bits[i]) ++i;
        if (i == CC_PP_HIDE_WORDS) return (int)index;
        slot=(slot+1)&(CC_PP_HIDE_SLOTS-1);
    }
    if (cc_pp_hide_count == CC_PP_HIDE_SETS) return -1;
    unsigned index=cc_pp_hide_count++;
    for (unsigned i=0; i<CC_PP_HIDE_WORDS; ++i) cc_pp_hide_sets[index][i]=bits[i];
    cc_pp_hide_slots[slot]=index+1;
    return (int)index;
}
static void cc_pp_hide_reset(void)
{
    unsigned empty[CC_PP_HIDE_WORDS]={0};
    cc_pp_hide_count=0;
    for (unsigned i=0; i<CC_PP_HIDE_SLOTS; ++i) cc_pp_hide_slots[i]=0;
    cc_pp_hide_intern(empty);
}
static int cc_pp_hide_contains(unsigned set, unsigned macro)
{
    if (set >= cc_pp_hide_count || macro >= CC_PP_MACROS) return 0;
    return (cc_pp_hide_sets[set][macro/32]>>(macro%32))&1u;
}
static int cc_pp_hide_add(unsigned set, unsigned macro)
{
    if (set >= cc_pp_hide_count || macro >= CC_PP_MACROS) return -1;
    unsigned bits[CC_PP_HIDE_WORDS];
    for (unsigned i=0; i<CC_PP_HIDE_WORDS; ++i) bits[i]=cc_pp_hide_sets[set][i];
    bits[macro/32] |= 1u<<(macro%32);
    return cc_pp_hide_intern(bits);
}
static int cc_pp_hide_merge(unsigned left, unsigned right, int intersection)
{
    if (left >= cc_pp_hide_count || right >= cc_pp_hide_count) return -1;
    unsigned bits[CC_PP_HIDE_WORDS];
    for (unsigned i=0; i<CC_PP_HIDE_WORDS; ++i)
        bits[i]=intersection ? cc_pp_hide_sets[left][i]&cc_pp_hide_sets[right][i]
                             : cc_pp_hide_sets[left][i]|cc_pp_hide_sets[right][i];
    return cc_pp_hide_intern(bits);
}
typedef struct { const unsigned char *text; unsigned size, kind, hidden, space; } cc_pp_token;
typedef struct { const unsigned char *text; unsigned size, at; int failed; } cc_pp_reader;
typedef struct {
    cc_pp_token name;
    unsigned first, count, parameter_first, parameter_count;
    int present, active, function, variadic;
} cc_pp_macro;
static cc_pp_macro cc_pp_macros[CC_PP_MACROS];
static cc_pp_token cc_pp_tokens[CC_PP_TOKENS];
static unsigned char cc_pp_text[CC_PP_TEXT], cc_pp_output[CC_PP_OUTPUT];
static unsigned cc_pp_macro_count, cc_pp_token_count, cc_pp_text_count, cc_pp_output_count;
static int cc_pp_enabled, cc_pp_skipping;
static int cc_pp_in_condition, cc_pp_query_enabled[5];
typedef struct { unsigned first, count; int variadic; } cc_pp_parameters;
static cc_pp_token cc_pp_parameter_names[CC_PP_PARAMETERS];
static unsigned cc_pp_parameter_count;

static int cc_pp_name(unsigned char byte)
{
    return (byte >= 'a' && byte <= 'z') || (byte >= 'A' && byte <= 'Z')
           || byte == '_' || byte == '$';
}
static int cc_pp_digit(unsigned char byte) { return byte >= '0' && byte <= '9'; }
static int cc_pp_equal(cc_pp_token a, cc_pp_token b)
{
    if (a.size != b.size) return 0;
    for (unsigned i=0; i<a.size; ++i) if (a.text[i] != b.text[i]) return 0;
    return 1;
}
static int cc_pp_is(cc_pp_token token, const char *text)
{
    unsigned i=0;
    while (text[i]) {
        if (i == token.size || token.text[i] != (unsigned char)text[i]) return 0;
        ++i;
    }
    return i == token.size;
}
static cc_pp_token cc_pp_next(cc_pp_reader *r)
{
    cc_pp_token token = {r->text+r->at, 0, 0, 0, 0};
    unsigned first, quote, before=r->at;
    while (r->at < r->size) {
        unsigned char c = r->text[r->at];
        if (c == ' ' || c == '\t' || c == '\v' || c == '\f') { ++r->at; continue; }
        if (c == '/' && r->at+1 < r->size && r->text[r->at+1] == '/') {
            r->at += 2;
            while (r->at < r->size && r->text[r->at] != '\n') ++r->at;
            continue;
        }
        if (c == '/' && r->at+1 < r->size && r->text[r->at+1] == '*') {
            r->at += 2;
            while (r->at+1 < r->size && !(r->text[r->at] == '*' && r->text[r->at+1] == '/')) {
                if (!r->text[r->at]) { r->failed=1; return token; }
                ++r->at;
            }
            if (r->at+1 == r->size || r->at == r->size) { r->failed=1; return token; }
            r->at += 2;
            continue;
        }
        break;
    }
    if (r->at == r->size) return token;
    first = r->at;
    token.text = r->text+first;
    token.space=first != before;
    quote = first;
    if (r->text[first] == 'L' || r->text[first] == 'u' || r->text[first] == 'U') {
        if (first+1 < r->size && (r->text[first+1] == '"' || r->text[first+1] == '\'')) quote=first+1;
        else if (r->text[first] == 'u' && first+2 < r->size && r->text[first+1] == '8'
                 && r->text[first+2] == '"') quote=first+2;
    }
    if (r->text[quote] == '"' || r->text[quote] == '\'') {
        unsigned char delimiter = r->text[quote];
        r->at = quote+1;
        while (r->at < r->size && r->text[r->at] != delimiter) {
            if (!r->text[r->at]) { r->failed=1; return token; }
            if (r->text[r->at] == '\n') {
                if (cc_pp_skipping) goto literal_done;
                r->failed=1; return token;
            }
            if (r->text[r->at++] == '\\') {
                if (r->at == r->size) {
                    if (cc_pp_skipping) goto literal_done;
                    r->failed=1; return token;
                }
                if (!r->text[r->at]) { r->failed=1; return token; }
                ++r->at;
            }
        }
        if (r->at == r->size) {
            if (cc_pp_skipping) goto literal_done;
            r->failed=1; return token;
        }
        ++r->at;
literal_done:
        token.kind=CC_PP_LITERAL;
    } else if (cc_pp_name(r->text[first])) {
        ++r->at;
        while (r->at < r->size && (cc_pp_name(r->text[r->at]) || cc_pp_digit(r->text[r->at]))) ++r->at;
        token.kind=CC_PP_IDENT;
    } else if (cc_pp_digit(r->text[first]) || (r->text[first] == '.' && first+1 < r->size && cc_pp_digit(r->text[first+1]))) {
        ++r->at;
        while (r->at < r->size) {
            unsigned char c=r->text[r->at], previous=r->text[r->at-1];
            if (cc_pp_name(c) || cc_pp_digit(c) || c == '.' || ((c == '+' || c == '-')
                && (previous == 'e' || previous == 'E' || previous == 'p' || previous == 'P'))) ++r->at;
            else break;
        }
        token.kind=CC_PP_NUMBER;
    } else {
        static const char *const pairs[] = {"++","--","->","<<",">>","<=",">=","==","!=","&&","||",
            "+=","-=","*=","/=","%=","&=","|=","^=","##",0};
        if (!r->text[first]) { r->failed=1; return token; }
        ++r->at;
        token.kind=r->text[first];
        if (first+2 < r->size && ((r->text[first] == '.' && r->text[first+1] == '.' && r->text[first+2] == '.')
            || ((r->text[first] == '<' || r->text[first] == '>') && r->text[first+1] == r->text[first] && r->text[first+2] == '='))) r->at=first+3;
        else if (first+1 < r->size) {
            for (unsigned i=0; pairs[i]; ++i) if (r->text[first] == (unsigned char)pairs[i][0]
                && r->text[first+1] == (unsigned char)pairs[i][1]) { r->at=first+2; break; }
        }
    }
    token.size=r->at-first;
    return token;
}
/* Called after the opening parenthesis. This parses definitions only;
 * production expansion still rejects function macros until substitution
 * and rescan are implemented together. */
static int cc_pp_read_parameters(cc_pp_reader *reader, cc_pp_parameters *parameters)
{
    unsigned first=cc_pp_parameter_count, count=0;
    int variadic=0;
    cc_pp_token token=cc_pp_next(reader);
    if (token.kind == ')') goto done;
    for (;;) {
        if (reader->failed || !token.kind || token.kind == '\n') goto failed;
        if (cc_pp_is(token,"...")) {
            token.text=(const unsigned char *)"__VA_ARGS__";
            token.size=11; token.kind=CC_PP_IDENT; variadic=1;
        } else if (token.kind != CC_PP_IDENT) goto failed;
        for (unsigned i=0; i<count; ++i)
            if (cc_pp_equal(token,cc_pp_parameter_names[first+i])) goto failed;
        if (cc_pp_parameter_count == CC_PP_PARAMETERS) goto failed;
        cc_pp_parameter_names[cc_pp_parameter_count++]=token; ++count;
        token=cc_pp_next(reader);
        if (!variadic && cc_pp_is(token,"...")) {
            variadic=1; token=cc_pp_next(reader);
        }
        if (variadic) { if (token.kind != ')') goto failed; break; }
        if (token.kind == ')') break;
        if (token.kind != ',') goto failed;
        token=cc_pp_next(reader);
    }
done:
    if (reader->failed) goto failed;
    parameters->first=first; parameters->count=count; parameters->variadic=variadic;
    return 1;
failed:
    cc_pp_parameter_count=first;
    return 0;
}
static int cc_pp_find(cc_pp_token name)
{
    for (unsigned i=0; i<cc_pp_macro_count; ++i) if (cc_pp_equal(name, cc_pp_macros[i].name)) return (int)i;
    return -1;
}
static int cc_pp_emit(cc_pp_token token)
{
    unsigned separator=token.kind != '\n';
    if (token.size > CC_PP_OUTPUT-cc_pp_output_count || separator > CC_PP_OUTPUT-cc_pp_output_count-token.size) return 0;
    for (unsigned i=0; i<token.size; ++i) cc_pp_output[cc_pp_output_count++]=token.text[i];
    if (separator) cc_pp_output[cc_pp_output_count++] = ' ';
    return 1;
}
static int cc_pp_paste(cc_pp_token a, cc_pp_token b, cc_pp_token *result)
{
    unsigned start=cc_pp_text_count;
    if (a.size > CC_PP_TEXT-start || b.size > CC_PP_TEXT-start-a.size) return 0;
    for (unsigned i=0; i<a.size; ++i) cc_pp_text[cc_pp_text_count++]=a.text[i];
    for (unsigned i=0; i<b.size; ++i) cc_pp_text[cc_pp_text_count++]=b.text[i];
    cc_pp_reader reader={cc_pp_text+start, a.size+b.size, 0, 0};
    *result=cc_pp_next(&reader);
    if (!result->kind || reader.failed || result->size != reader.size) return 0;
    cc_pp_token tail=cc_pp_next(&reader);
    if (reader.failed || tail.kind) return 0;
    if (a.hidden || b.hidden) {
        int hidden=cc_pp_hide_merge(a.hidden,b.hidden,1);
        if (hidden < 0) return 0;
        result->hidden=(unsigned)hidden;
    }
    result->space=a.space;
    return 1;
}
static int cc_pp_string_byte(unsigned char byte)
{
    if (cc_pp_text_count == CC_PP_TEXT) return 0;
    cc_pp_text[cc_pp_text_count++]=byte;
    return 1;
}
static int cc_pp_stringify(cc_pp_reader reader, cc_pp_token *result)
{
    unsigned start=cc_pp_text_count;
    int previous=0, space=0;
    if (!cc_pp_string_byte('"')) goto failed;
    for (;;) {
        unsigned before=reader.at;
        cc_pp_token token=cc_pp_next(&reader);
        if (reader.failed) goto failed;
        if (!token.kind) break;
        if (token.kind == '\n') { space=1; continue; }
        if (previous && (space || (unsigned)(token.text-reader.text) != before))
            if (!cc_pp_string_byte(' ')) goto failed;
        for (unsigned i=0; i<token.size; ++i) {
            unsigned char byte=token.text[i];
            if (token.kind == CC_PP_LITERAL && (byte == '"' || byte == '\\'))
                if (!cc_pp_string_byte('\\')) goto failed;
            if (!cc_pp_string_byte(byte)) goto failed;
        }
        previous=1; space=0;
    }
    if (!cc_pp_string_byte('"')) goto failed;
    *result=(cc_pp_token){cc_pp_text+start,cc_pp_text_count-start,CC_PP_LITERAL,0,0};
    return 1;
failed:
    cc_pp_text_count=start;
    return 0;
}
static int cc_pp_stringify_tokens(const cc_pp_token *tokens, unsigned count, cc_pp_token *result)
{
    unsigned start=cc_pp_text_count;
    int previous=0, space=0;
    if (!cc_pp_string_byte('"')) goto failed;
    for (unsigned at=0; at<count; ++at) {
        cc_pp_token token=tokens[at];
        if (token.kind == '\n') { space=1; continue; }
        if (previous && (space || token.space)) if (!cc_pp_string_byte(' ')) goto failed;
        for (unsigned i=0; i<token.size; ++i) {
            unsigned char byte=token.text[i];
            if (token.kind == CC_PP_LITERAL && (byte == '"' || byte == '\\'))
                if (!cc_pp_string_byte('\\')) goto failed;
            if (!cc_pp_string_byte(byte)) goto failed;
        }
        previous=1; space=0;
    }
    if (!cc_pp_string_byte('"')) goto failed;
    *result=(cc_pp_token){cc_pp_text+start,cc_pp_text_count-start,CC_PP_LITERAL,0,0};
    return 1;
failed:
    cc_pp_text_count=start; return 0;
}
typedef struct {
    cc_pp_reader spelling;
    const cc_pp_token *raw, *expanded;
    unsigned raw_count, expanded_count;
    int omitted;
} cc_pp_argument;
/* Reader starts after '('; argument views retain original spacing for #. */
static int cc_pp_read_arguments(cc_pp_reader *reader, cc_pp_parameters parameters,
                                cc_pp_reader *arguments, int *omitted)
{
    unsigned first=reader->at, index=0, depth=0;
    int any=0;
    if (parameters.variadic && !parameters.count) return 0;
    for (;;) {
        cc_pp_token token=cc_pp_next(reader);
        if (reader->failed || !token.kind) return 0;
        if (token.kind == '\n') continue;
        int closing=token.kind == ')' && !depth;
        int separator=token.kind == ',' && !depth;
        if (closing && !any && !index && !parameters.count) return 1;
        if (closing || (separator && !(parameters.variadic && index+1 == parameters.count))) {
            if (index >= parameters.count) return 0;
            unsigned end=(unsigned)(token.text-reader->text);
            arguments[index]=(cc_pp_reader){reader->text+first,end-first,0,0};
            omitted[index]=0; ++index;
            if (closing) {
                if (parameters.variadic && index+1 == parameters.count) {
                    arguments[index]=(cc_pp_reader){reader->text+end,0,0,0};
                    omitted[index++]=1;
                } else if (parameters.variadic && parameters.count == 1 && !any)
                    omitted[0]=1;
                return index == parameters.count;
            }
            first=reader->at; any=0; continue;
        }
        if (token.kind == '(') { if (depth == 64) return 0; ++depth; }
        else if (token.kind == ')') --depth;
        any=1;
    }
}
static int cc_pp_parameter_index(cc_pp_parameters parameters, cc_pp_token token)
{
    if (token.kind != CC_PP_IDENT) return -1;
    for (unsigned i=0; i<parameters.count; ++i)
        if (cc_pp_equal(token,cc_pp_parameter_names[parameters.first+i])) return (int)i;
    return -1;
}
static unsigned cc_pp_va_opt_end(const cc_pp_token *body, unsigned size, unsigned at)
{
    if (at+1 >= size || body[at+1].kind != '(') return 0;
    unsigned depth=1;
    for (unsigned i=at+2; i<size; ++i) {
        if (cc_pp_is(body[i],"__VA_OPT__")) return 0;
        if (body[i].kind == '(') ++depth;
        else if (body[i].kind == ')' && !--depth) return i;
    }
    return 0;
}
static int cc_pp_substitute(const cc_pp_token *body, unsigned size,
                            cc_pp_parameters parameters, const cc_pp_argument *arguments,
                            cc_pp_token *output, unsigned capacity, unsigned *count)
{
    unsigned used=0, text_start=cc_pp_text_count;
    int paste=0, gap=0, comma_paste=0;
    cc_pp_token empty={0,0,0,0,0};
    cc_pp_token *option=0;
    for (unsigned i=0; i<size; ++i) {
        cc_pp_token token=body[i], single;
        unsigned leading=token.space;
        const cc_pp_token *piece=&token;
        unsigned length=1;
        if (cc_pp_is(token,"##")) {
            if (comma_paste) { comma_paste=0; continue; }
            if (!used || i+1 == size) goto failed;
            paste=1; continue;
        }
        if (parameters.variadic && token.kind == ',' && i+2 < size
            && cc_pp_is(body[i+1],"##")
            && cc_pp_parameter_index(parameters,body[i+2]) == (int)parameters.count-1) {
            comma_paste=1;
            if (arguments[parameters.count-1].omitted) continue;
        }
        int stringify=cc_pp_is(token,"#");
        if (stringify) { if (++i == size) goto failed; token=body[i]; }
        int parameter=cc_pp_parameter_index(parameters,token);
        int adjacent=paste || (i+1 < size && cc_pp_is(body[i+1],"##"));
        if (parameters.variadic && cc_pp_is(token,"__VA_OPT__")) {
            unsigned end=cc_pp_va_opt_end(body,size,i);
            if (!end) goto failed;
            length=0; piece=&empty;
            if (arguments[parameters.count-1].expanded_count) {
                option=capacity ? cc_pp_allocate(capacity*sizeof(*option)) : 0;
                if (capacity && !option) goto failed;
                if (!cc_pp_substitute(body+i+2,end-i-2,parameters,arguments,option,capacity,&length)) goto failed;
                piece=option;
            }
            i=end; adjacent=paste || (i+1 < size && cc_pp_is(body[i+1],"##"));
            if (stringify) {
                if (!cc_pp_stringify_tokens(piece,length,&single)) goto failed;
                piece=&single; length=1;
            } else if (!length && adjacent) { piece=&empty; length=1; }
        } else if (stringify) {
            if (parameter < 0) goto failed;
            const cc_pp_argument *argument=arguments+parameter;
            if (argument->spelling.text) {
                if (!cc_pp_stringify(argument->spelling,&single)) goto failed;
            } else if (!cc_pp_stringify_tokens(argument->raw,argument->raw_count,&single)) goto failed;
            piece=&single;
        } else if (parameter >= 0) {
            const cc_pp_argument *argument=arguments+parameter;
            piece=adjacent ? argument->raw : argument->expanded;
            length=adjacent ? argument->raw_count : argument->expanded_count;
            if (!length && adjacent) { piece=&empty; length=1; }
        }
        unsigned at=0;
        if (paste) {
            if (!length) goto failed;
            cc_pp_token left=output[used-1], right=piece[0];
            if (!left.kind) output[used-1]=right;
            else if (right.kind && !cc_pp_paste(left,right,output+used-1)) goto failed;
            at=1; paste=0;
        }
        for (; at<length; ++at) {
            if (used == capacity) goto failed;
            output[used++]=piece[at];
            if (!at) { output[used-1].space=leading || gap; gap=0; }
        }
        if (!length && leading) gap=1;
        cc_pp_free(option); option=0;
    }
    *count=0;
    for (unsigned i=0; i<used; ++i) if (output[i].kind) output[(*count)++]=output[i];
    return 1;
failed:
    cc_pp_free(option);
    cc_pp_text_count=text_start; *count=0;
    return 0;
}
#define CC_PP_NODES 32768
typedef struct { cc_pp_token token; unsigned next, frozen; } cc_pp_node;
static cc_pp_node cc_pp_nodes[CC_PP_NODES+1];
static unsigned cc_pp_node_count, cc_pp_node_free;
typedef struct { cc_pp_macro macro; unsigned index, next; } cc_pp_frozen;
static cc_pp_frozen cc_pp_frozen_macros[65];
static unsigned cc_pp_frozen_count, cc_pp_frozen_free, cc_pp_blocked;
static int cc_pp_allow_incomplete;
static unsigned cc_pp_freeze(cc_pp_macro macro, unsigned index)
{
    unsigned slot;
    if (cc_pp_frozen_free) {
        slot=cc_pp_frozen_free; cc_pp_frozen_free=cc_pp_frozen_macros[slot].next;
    } else {
        if (cc_pp_frozen_count == 64) return 0;
        slot=++cc_pp_frozen_count;
    }
    cc_pp_frozen_macros[slot]=(cc_pp_frozen){macro,index,0};
    return slot;
}
static unsigned cc_pp_node_new(cc_pp_token token)
{
    unsigned index;
    if (cc_pp_node_free) {
        index=cc_pp_node_free; cc_pp_node_free=cc_pp_nodes[index].next;
    } else {
        if (cc_pp_node_count == CC_PP_NODES) return 0;
        index=++cc_pp_node_count;
    }
    cc_pp_nodes[index]=(cc_pp_node){token,0,0};
    return index;
}
static void cc_pp_node_release(unsigned index)
{
    unsigned frozen=cc_pp_nodes[index].frozen;
    if (frozen) {
        cc_pp_frozen_macros[frozen].next=cc_pp_frozen_free; cc_pp_frozen_free=frozen;
    }
    cc_pp_nodes[index].next=cc_pp_node_free; cc_pp_node_free=index;
}
static void cc_pp_list_release(unsigned head)
{
    while (head) { unsigned next=cc_pp_nodes[head].next; cc_pp_node_release(head); head=next; }
}
typedef struct { unsigned first, end, count; int omitted; } cc_pp_argument_view;
static unsigned cc_pp_call_views(unsigned opening, cc_pp_parameters parameters, cc_pp_argument_view *views)
{
    unsigned node=cc_pp_nodes[opening].next, first=node, count=0, index=0, depth=0;
    int any=0;
    if (parameters.count > 128) return 0;
    while (node) {
        cc_pp_token token=cc_pp_nodes[node].token;
        if (token.kind == '\n') { node=cc_pp_nodes[node].next; continue; }
        int closing=token.kind == ')' && !depth;
        int separator=token.kind == ',' && !depth;
        if (closing && !any && !index && !parameters.count) return node;
        if (closing || (separator && !(parameters.variadic && index+1 == parameters.count))) {
            if (index >= parameters.count) return 0;
            views[index++]=(cc_pp_argument_view){first,node,count,0};
            if (closing) {
                if (parameters.variadic && index+1 == parameters.count)
                    views[index++]=(cc_pp_argument_view){node,node,0,1};
                else if (parameters.variadic && parameters.count == 1 && !any) views[0].omitted=1;
                return index == parameters.count ? node : 0;
            }
            first=cc_pp_nodes[node].next; count=0; any=0;
        } else {
            if (token.kind == '(') { if (depth == 64) return 0; ++depth; }
            else if (token.kind == ')') --depth;
            ++count; any=1;
        }
        node=cc_pp_nodes[node].next;
    }
    return 0;
}
static int cc_pp_rescan_depth(unsigned *head, unsigned depth);
static int cc_pp_function_replace(cc_pp_macro *macro, unsigned opening, unsigned depth,
                                   unsigned *replacement, unsigned *tail, unsigned *closing)
{
    cc_pp_parameters parameters={macro->parameter_first,macro->parameter_count,macro->variadic};
    cc_pp_argument_view views[128]; cc_pp_argument arguments[128]={0};
    cc_pp_token *output=0;
    *replacement=*tail=0;
    *closing=cc_pp_call_views(opening,parameters,views);
    if (!*closing || depth == 64) return 0;
    for (unsigned i=0; i<parameters.count; ++i) {
        cc_pp_token *raw=views[i].count ? cc_pp_allocate(views[i].count*sizeof(*raw)) : 0;
        if (views[i].count && !raw) goto failed;
        arguments[i].raw=raw; arguments[i].raw_count=views[i].count;
        arguments[i].omitted=views[i].omitted;
        unsigned at=0; int space=0;
        for (unsigned node=views[i].first; node != views[i].end; node=cc_pp_nodes[node].next) {
            cc_pp_token token=cc_pp_nodes[node].token;
            if (token.kind == '\n') { space=1; continue; }
            if (space) token.space=1;
            raw[at++]=token; space=0;
        }
        int needed=0;
        for (unsigned j=0; j<macro->count; ++j) {
            cc_pp_token token=cc_pp_tokens[macro->first+j];
            if (parameters.variadic && i+1 == parameters.count && cc_pp_is(token,"__VA_OPT__")) needed=1;
            if (cc_pp_is(token,"#")) {
                if (parameters.variadic && i+1 == parameters.count && j+1 < macro->count
                    && cc_pp_is(cc_pp_tokens[macro->first+j+1],"__VA_OPT__")) needed=1;
                ++j; continue;
            }
            if (cc_pp_parameter_index(parameters,token) != (int)i) continue;
            if (j && cc_pp_is(cc_pp_tokens[macro->first+j-1],"##")) {
                if (!(parameters.variadic && i+1 == parameters.count && j>=2
                      && cc_pp_tokens[macro->first+j-2].kind == ',')) continue;
            }
            if (j+1 < macro->count && cc_pp_is(cc_pp_tokens[macro->first+j+1],"##")) continue;
            needed=1;
        }
        arguments[i].expanded=raw; arguments[i].expanded_count=views[i].count;
        if (!needed) continue;
        unsigned head=0, last=0;
        for (unsigned j=0; j<views[i].count; ++j) {
            unsigned node=cc_pp_node_new(raw[j]);
            if (!node) { cc_pp_list_release(head); goto failed; }
            if (last) cc_pp_nodes[last].next=node; else head=node;
            last=node;
        }
        if (!cc_pp_rescan_depth(&head,depth+1)) { cc_pp_list_release(head); goto failed; }
        unsigned count=0;
        for (unsigned node=head; node; node=cc_pp_nodes[node].next) ++count;
        cc_pp_token *expanded=count ? cc_pp_allocate(count*sizeof(*expanded)) : 0;
        if (count && !expanded) { cc_pp_list_release(head); goto failed; }
        at=0;
        for (unsigned node=head; node; node=cc_pp_nodes[node].next) expanded[at++]=cc_pp_nodes[node].token;
        cc_pp_list_release(head);
        arguments[i].expanded=expanded; arguments[i].expanded_count=count;
    }
    unsigned capacity=macro->count;
    for (unsigned j=0; j<macro->count; ++j) {
        int parameter=cc_pp_parameter_index(parameters,cc_pp_tokens[macro->first+j]);
        if (parameter >= 0) {
            unsigned count=arguments[parameter].raw_count;
            if (arguments[parameter].expanded_count > count) count=arguments[parameter].expanded_count;
            if (count > CC_PP_NODES-capacity) goto failed;
            capacity+=count;
        }
    }
    output=capacity ? cc_pp_allocate(capacity*sizeof(*output)) : 0;
    if (capacity && !output) goto failed;
    unsigned count;
    if (!cc_pp_substitute(cc_pp_tokens+macro->first,macro->count,parameters,arguments,output,capacity,&count)) goto failed;
    for (unsigned i=0; i<count; ++i) {
        unsigned node=cc_pp_node_new(output[i]);
        if (!node) goto failed;
        if (*tail) cc_pp_nodes[*tail].next=node; else *replacement=node;
        *tail=node;
    }
    cc_pp_free(output);
    for (unsigned i=0; i<parameters.count; ++i) {
        if (arguments[i].expanded != arguments[i].raw) cc_pp_free((void *)arguments[i].expanded);
        cc_pp_free((void *)arguments[i].raw);
    }
    return 1;
failed:
    cc_pp_list_release(*replacement); *replacement=*tail=0;
    cc_pp_free(output);
    for (unsigned i=0; i<parameters.count; ++i) {
        if (arguments[i].expanded != arguments[i].raw) cc_pp_free((void *)arguments[i].expanded);
        cc_pp_free((void *)arguments[i].raw);
    }
    return 0;
}
static int cc_pp_query_kind(cc_pp_token token);
static int cc_pp_query_symbol(cc_pp_token token);
static int cc_pp_is_defined(cc_pp_token token);
static int cc_pp_query_expand(unsigned *cursor, int kind, unsigned depth);
static cc_pp_token cc_pp_condition_token(cc_pp_reader *reader, unsigned *state);
static int cc_pp_rescan_depth(unsigned *head, unsigned depth)
{
    unsigned *cursor=head;
    while (*cursor) {
        unsigned current=*cursor;
        cc_pp_token token=cc_pp_nodes[current].token;
        int query=cc_pp_query_kind(token);
        if (query) {
            if (query<=2 && !cc_pp_in_condition) return 0;
            if (!cc_pp_query_expand(cursor,query,depth)) return 0;
            continue;
        }
        unsigned frozen=cc_pp_nodes[current].frozen;
        int index=frozen ? (int)cc_pp_frozen_macros[frozen].index
                         : (token.kind == CC_PP_IDENT ? cc_pp_find(token) : -1);
        cc_pp_macro *macro=frozen ? &cc_pp_frozen_macros[frozen].macro
                                 : (index >= 0 ? cc_pp_macros+index : 0);
        if (index < 0 || !macro->present || cc_pp_hide_contains(token.hidden,(unsigned)index)) {
            cursor=&cc_pp_nodes[current].next; continue;
        }
        int hidden=cc_pp_hide_add(token.hidden,(unsigned)index);
        if (hidden < 0) return 0;
        unsigned replacement=0, tail=0;
        unsigned consumed=current;
        if (macro->function) {
            unsigned opening=cc_pp_nodes[current].next;
            while (opening && cc_pp_nodes[opening].token.kind == '\n') opening=cc_pp_nodes[opening].next;
            if (!opening || cc_pp_nodes[opening].token.kind != '(') { cursor=&cc_pp_nodes[current].next; continue; }
            if (cc_pp_allow_incomplete && !depth) {
                unsigned balance=1, node=cc_pp_nodes[opening].next;
                while (node) {
                    unsigned kind=cc_pp_nodes[node].token.kind;
                    if (kind == '(') ++balance;
                    else if (kind == ')' && !--balance) break;
                    node=cc_pp_nodes[node].next;
                }
                if (!node) {
                    if (!frozen) {
                        frozen=cc_pp_freeze(*macro,(unsigned)index);
                        if (!frozen) return 0;
                        cc_pp_nodes[current].frozen=frozen;
                    }
                    cc_pp_blocked=current; return 1;
                }
            }
            if (!cc_pp_function_replace(macro,opening,depth,&replacement,&tail,&consumed)) return 0;
            hidden=cc_pp_hide_merge(token.hidden,cc_pp_nodes[consumed].token.hidden,1);
            if (hidden >= 0) hidden=cc_pp_hide_add((unsigned)hidden,(unsigned)index);
            if (hidden < 0) { cc_pp_list_release(replacement); return 0; }
            for (unsigned node=replacement; node; node=cc_pp_nodes[node].next) {
                int merged=cc_pp_hide_merge(cc_pp_nodes[node].token.hidden,(unsigned)hidden,0);
                if (merged < 0) { cc_pp_list_release(replacement); return 0; }
                cc_pp_nodes[node].token.hidden=(unsigned)merged;
            }
            if (replacement) cc_pp_nodes[replacement].token.space=token.space;
        } else for (unsigned i=0; i<macro->count; ++i) {
            cc_pp_token next=cc_pp_tokens[macro->first+i];
            while (i+1 < macro->count && cc_pp_is(cc_pp_tokens[macro->first+i+1],"##")) {
                unsigned right=i+1;
                while (right < macro->count && cc_pp_is(cc_pp_tokens[macro->first+right],"##")) ++right;
                if (right == macro->count || !cc_pp_paste(next,cc_pp_tokens[macro->first+right],&next)) {
                    cc_pp_list_release(replacement); return 0;
                }
                i=right;
            }
            int merged=cc_pp_hide_merge(next.hidden,(unsigned)hidden,0);
            if (merged < 0) { cc_pp_list_release(replacement); return 0; }
            next.hidden=(unsigned)merged;
            if (!replacement) next.space=token.space;
            unsigned node=cc_pp_node_new(next);
            if (!node) { cc_pp_list_release(replacement); return 0; }
            if (tail) cc_pp_nodes[tail].next=node; else replacement=node;
            tail=node;
        }
        unsigned rest=cc_pp_nodes[consumed].next;
        if (tail) cc_pp_nodes[tail].next=rest;
        else if (rest && token.space) cc_pp_nodes[rest].token.space=1;
        *cursor=replacement ? replacement : rest;
        while (current != rest) {
            unsigned next=cc_pp_nodes[current].next; cc_pp_node_release(current); current=next;
        }
    }
    return 1;
}
static int cc_pp_rescan(unsigned *head) { return cc_pp_rescan_depth(head,0); }
static int cc_pp_flush(unsigned head)
{
    int success=cc_pp_rescan(&head);
    if (success) for (unsigned node=head; node; node=cc_pp_nodes[node].next)
        if (!cc_pp_emit(cc_pp_nodes[node].token)) { success=0; break; }
    cc_pp_list_release(head);
    return success;
}
static int cc_pp_flush_prefix(unsigned *head)
{
    cc_pp_allow_incomplete=1; cc_pp_blocked=0;
    int success=cc_pp_rescan(head);
    cc_pp_allow_incomplete=0;
    if (!success) return 0;
    while (*head && *head != cc_pp_blocked) {
        unsigned node=*head;
        if (!cc_pp_emit(cc_pp_nodes[node].token)) return 0;
        *head=cc_pp_nodes[node].next; cc_pp_node_release(node);
    }
    return 1;
}
static int cc_pp_expand(cc_pp_token token, unsigned depth)
{
    (void)depth;
    unsigned head=cc_pp_node_new(token);
    return head && cc_pp_flush(head);
}
#include "preprocess_condition.h"
#include "preprocess_include.h"
#include "preprocess_queries.h"
static int cc_pp_directive(cc_pp_reader *reader)
{
    cc_pp_token directive=cc_pp_next(reader), name, token;
    if (!directive.kind || directive.kind == '\n') return !reader->failed;
    int conditional=cc_pp_condition_directive(reader,directive);
    if (conditional>=0) return conditional;
    if (!cc_pp_enabled) return cc_pp_skip_line(reader);
    if (cc_pp_is(directive,"include") || cc_pp_is(directive,"include_next"))
        return cc_pp_include_directive(reader,cc_pp_is(directive,"include_next"));
    if (cc_pp_is(directive,"pragma")) return cc_pp_pragma(reader);
    int define=cc_pp_is(directive, "define"), undef=cc_pp_is(directive, "undef");
    if (!define && !undef) return 0;
    name=cc_pp_next(reader);
    if (reader->failed || name.kind != CC_PP_IDENT) return 0;
    token=cc_pp_next(reader);
    if (undef) {
        int query=cc_pp_query_symbol(name);
        if (query) cc_pp_query_enabled[query-1]=0;
    }
    int index=cc_pp_find(name);
    if (index < 0) {
        if (!define) return (!token.kind || token.kind == '\n') && !reader->failed;
        if (cc_pp_macro_count == CC_PP_MACROS) return 0;
        index=(int)cc_pp_macro_count++;
        cc_pp_macros[index].name=name;
    }
    cc_pp_macro *macro=cc_pp_macros+index;
    if (undef) {
        if (token.kind && token.kind != '\n') return 0;
        macro->present=0;
        return !reader->failed;
    }
    macro->function=macro->variadic=0;
    macro->parameter_first=macro->parameter_count=0;
    if (token.kind == '(' && token.text == name.text+name.size) {
        cc_pp_parameters parameters;
        if (!cc_pp_read_parameters(reader,&parameters)) return 0;
        macro->function=1; macro->variadic=parameters.variadic;
        macro->parameter_first=parameters.first; macro->parameter_count=parameters.count;
        token=cc_pp_next(reader);
    }
    macro->first=cc_pp_token_count;
    while (token.kind && token.kind != '\n') {
        if (reader->failed || cc_pp_token_count == CC_PP_TOKENS) return 0;
        if (cc_pp_is(token,"##") && cc_pp_token_count == macro->first) return 0;
        cc_pp_tokens[cc_pp_token_count++]=token;
        token=cc_pp_next(reader);
    }
    macro->count=cc_pp_token_count-macro->first;
    if (macro->count && cc_pp_is(cc_pp_tokens[cc_pp_token_count-1],"##")) return 0;
    if (macro->function) {
        cc_pp_parameters parameters={macro->parameter_first,macro->parameter_count,macro->variadic};
        if (parameters.variadic) for (unsigned i=0; i<macro->count; ++i)
            if (cc_pp_is(cc_pp_tokens[macro->first+i],"__VA_OPT__")) {
                unsigned end=cc_pp_va_opt_end(cc_pp_tokens+macro->first,macro->count,i);
                if (!end) return 0;
                if (end>i+2 && (cc_pp_is(cc_pp_tokens[macro->first+i+2],"##")
                    || cc_pp_is(cc_pp_tokens[macro->first+end-1],"##"))) return 0;
                i=end;
            }
        for (unsigned i=0; i<macro->count; ++i) if (cc_pp_is(cc_pp_tokens[macro->first+i],"#")) {
            if (++i == macro->count) return 0;
            if (cc_pp_parameter_index(parameters,cc_pp_tokens[macro->first+i]) < 0
                && !(parameters.variadic && cc_pp_is(cc_pp_tokens[macro->first+i],"__VA_OPT__"))) return 0;
        }
    }
    macro->present=1;
    return !reader->failed;
}
static int cc_preprocess_macros(unsigned char *source, unsigned size)
{
    cc_pp_macro_count=cc_pp_token_count=cc_pp_text_count=cc_pp_output_count=0;
    cc_pp_parameter_count=cc_pp_node_count=cc_pp_node_free=0;
    cc_pp_frozen_count=cc_pp_frozen_free=cc_pp_blocked=0; cc_pp_allow_incomplete=0;
    cc_pp_hide_reset();
    cc_pp_group_count=cc_pp_group_floor=0; cc_pp_enabled=1; cc_pp_skipping=0;
    cc_pp_in_condition=0;
    for (unsigned i=0;i<5;++i) cc_pp_query_enabled[i]=1;
    cc_input_file_count=cc_file_root_count=0;
    cc_pp_include_depth=0; cc_pp_current_file=CC_FILES_MAX;
    cc_pp_current_root=cc_pp_include_file=-1;
    for (unsigned i=0;i<CC_FILES_MAX;++i) cc_pp_file_once[i]=0;
    for (unsigned i=0; i<CC_PP_MACROS; ++i) {
        cc_pp_macros[i].present=cc_pp_macros[i].active=0;
        cc_pp_macros[i].count=0;
    }
    cc_pp_reader reader={source,size,0,0};
    if (cc_files_magic(source,size)) {
        if (!cc_files_decode(source,size)) return -1;
        for (unsigned i=0;i<cc_input_file_count;++i)
            cc_input_files[i].size=cc_preprocess_phase2_text(cc_input_files[i].data,cc_input_files[i].size);
        cc_pp_current_file=cc_main_file;
        reader=(cc_pp_reader){cc_input_files[cc_main_file].data,cc_input_files[cc_main_file].size,0,0};
    }
    int beginning=1;
    unsigned head=0, tail=0;
    for (;;) {
        cc_pp_skipping=!cc_pp_enabled;
        cc_pp_token token=cc_pp_next(&reader);
        if (reader.failed) return -1;
        if (!token.kind) {
            if (cc_pp_group_count!=cc_pp_group_floor) return -1;
            if (!cc_pp_include_depth) break;
            if (!cc_pp_flush(head)) return -1;
            head=tail=0;
            cc_pp_include_frame frame=cc_pp_include_stack[--cc_pp_include_depth];
            reader=frame.reader; cc_pp_current_file=frame.file;
            cc_pp_current_root=frame.root; cc_pp_group_floor=frame.floor;
            beginning=1;
            continue;
        }
        if (beginning && cc_pp_is(token,"#")) {
            if (!cc_pp_flush_prefix(&head)) return -1;
            tail=head;
            while (tail && cc_pp_nodes[tail].next) tail=cc_pp_nodes[tail].next;
            if (!cc_pp_directive(&reader)) return -1;
            if (cc_pp_include_file>=0) {
                if (cc_pp_include_depth==CC_PP_INCLUDE_DEPTH) return -1;
                cc_pp_include_stack[cc_pp_include_depth++]=(cc_pp_include_frame){
                    reader,cc_pp_current_file,cc_pp_group_floor,cc_pp_current_root};
                cc_pp_current_file=(unsigned)cc_pp_include_file;
                cc_pp_current_root=cc_pp_include_root; cc_pp_include_file=-1;
                cc_pp_group_floor=cc_pp_group_count;
                cc_input_file file=cc_input_files[cc_pp_current_file];
                reader=(cc_pp_reader){file.data,file.size,0,0};
            }
            beginning=1;
        } else {
            if (cc_pp_enabled) {
                unsigned node=cc_pp_node_new(token);
                if (!node) return -1;
                if (tail) cc_pp_nodes[tail].next=node; else head=node;
                tail=node;
            }
            beginning=token.kind == '\n';
        }
    }
    if (cc_pp_group_count || !cc_pp_flush(head)) return -1;
    for (unsigned i=0; i<cc_pp_output_count; ++i) source[i]=cc_pp_output[i];
    return (int)cc_pp_output_count;
}
