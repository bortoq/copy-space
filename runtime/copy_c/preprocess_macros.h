/* Guest preprocessing. All pointers refer to guest memory; no file or host
 * service participates in token recognition or macro substitution. */
#define CC_PP_IDENT 256
#define CC_PP_NUMBER 257
#define CC_PP_LITERAL 258
#define CC_PP_MACROS 512
#define CC_PP_TOKENS 32768
#define CC_PP_TEXT 262144
#define CC_PP_OUTPUT 1048576
typedef struct { const unsigned char *text; unsigned size, kind; } cc_pp_token;
typedef struct { const unsigned char *text; unsigned size, at; int failed; } cc_pp_reader;
typedef struct { cc_pp_token name; unsigned first, count; int present, active; } cc_pp_macro;
static cc_pp_macro cc_pp_macros[CC_PP_MACROS];
static cc_pp_token cc_pp_tokens[CC_PP_TOKENS];
static unsigned char cc_pp_text[CC_PP_TEXT], cc_pp_output[CC_PP_OUTPUT];
static unsigned cc_pp_macro_count, cc_pp_token_count, cc_pp_text_count, cc_pp_output_count;

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
    cc_pp_token token = {r->text+r->at, 0, 0};
    unsigned first, quote;
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
            if (!r->text[r->at] || r->text[r->at] == '\n') { r->failed=1; return token; }
            if (r->text[r->at++] == '\\') {
                if (r->at == r->size || !r->text[r->at]) { r->failed=1; return token; }
                ++r->at;
            }
        }
        if (r->at == r->size) { r->failed=1; return token; }
        ++r->at;
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
    return !reader.failed && !tail.kind;
}
static int cc_pp_expand(cc_pp_token token, unsigned depth)
{
    int index=token.kind == CC_PP_IDENT ? cc_pp_find(token) : -1;
    if (index < 0 || !cc_pp_macros[index].present || cc_pp_macros[index].active) return cc_pp_emit(token);
    if (depth == 64) return 0;
    cc_pp_macro *macro=cc_pp_macros+index;
    macro->active=1;
    for (unsigned i=0; i<macro->count; ++i) {
        cc_pp_token next=cc_pp_tokens[macro->first+i];
        while (i+1 < macro->count && cc_pp_is(cc_pp_tokens[macro->first+i+1], "##")) {
            if (i+2 >= macro->count || !cc_pp_paste(next, cc_pp_tokens[macro->first+i+2], &next)) return 0;
            i += 2;
        }
        if (!cc_pp_expand(next, depth+1)) return 0;
    }
    macro->active=0;
    return 1;
}
static int cc_pp_directive(cc_pp_reader *reader)
{
    cc_pp_token directive=cc_pp_next(reader), name, token;
    if (!directive.kind || directive.kind == '\n') return !reader->failed;
    int define=cc_pp_is(directive, "define"), undef=cc_pp_is(directive, "undef");
    if (!define && !undef) return 0;
    name=cc_pp_next(reader);
    if (reader->failed || name.kind != CC_PP_IDENT) return 0;
    token=cc_pp_next(reader);
    if (define && token.kind == '(' && token.text == name.text+name.size) return 0;
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
    macro->first=cc_pp_token_count;
    while (token.kind && token.kind != '\n') {
        if (reader->failed || cc_pp_token_count == CC_PP_TOKENS) return 0;
        if (cc_pp_is(token,"##") && (cc_pp_token_count == macro->first || cc_pp_is(cc_pp_tokens[cc_pp_token_count-1],"##"))) return 0;
        cc_pp_tokens[cc_pp_token_count++]=token;
        token=cc_pp_next(reader);
    }
    macro->count=cc_pp_token_count-macro->first;
    if (macro->count && cc_pp_is(cc_pp_tokens[cc_pp_token_count-1],"##")) return 0;
    macro->present=1;
    return !reader->failed;
}
static int cc_preprocess_macros(unsigned char *source, unsigned size)
{
    cc_pp_macro_count=cc_pp_token_count=cc_pp_text_count=cc_pp_output_count=0;
    for (unsigned i=0; i<CC_PP_MACROS; ++i) {
        cc_pp_macros[i].present=cc_pp_macros[i].active=0;
        cc_pp_macros[i].count=0;
    }
    cc_pp_reader reader={source,size,0,0};
    int beginning=1;
    for (;;) {
        cc_pp_token token=cc_pp_next(&reader);
        if (reader.failed) return -1;
        if (!token.kind) break;
        if (beginning && cc_pp_is(token,"#")) {
            if (!cc_pp_directive(&reader)) return -1;
            beginning=1;
        } else {
            if (!cc_pp_expand(token,0)) return -1;
            beginning=token.kind == '\n';
        }
    }
    for (unsigned i=0; i<cc_pp_output_count; ++i) source[i]=cc_pp_output[i];
    return (int)cc_pp_output_count;
}
