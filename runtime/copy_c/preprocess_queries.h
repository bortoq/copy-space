/* Builtin preprocessing executes in the guest. Header queries share lookup
 * without pushing a reader; capabilities describe implemented frontend support. */
static int cc_pp_query_symbol(cc_pp_token token)
{
    if (token.kind!=CC_PP_IDENT) return 0;
    return cc_pp_is(token,"__has_include") ? 1 : cc_pp_is(token,"__has_include_next") ? 2
         : cc_pp_is(token,"__has_attribute") ? 3 : cc_pp_is(token,"__has_builtin") ? 4
         : cc_pp_is(token,"__COPYSPACE__") ? 5 : 0;
}
static int cc_pp_query_kind(cc_pp_token token)
{
    int symbol=cc_pp_query_symbol(token);
    if (!symbol) return 0;
    int index=cc_pp_find(token);
    return symbol && cc_pp_query_enabled[symbol-1] && (index<0 || !cc_pp_macros[index].present) ? symbol : 0;
}
static int cc_pp_is_defined(cc_pp_token token)
{
    int index=cc_pp_find(token);
    return (index>=0 && cc_pp_macros[index].present) || cc_pp_query_kind(token);
}
static int cc_pp_query_lex_kind(cc_pp_token token)
{
    if (token.kind!=CC_PP_IDENT) return 0;
    for (unsigned i=0;i<=CC_PP_MACROS;++i) {
        int kind=cc_pp_query_kind(token);
        if (kind) return kind;
        int index=cc_pp_find(token);
        if (index<0) return 0;
        cc_pp_macro macro=cc_pp_macros[index];
        if (!macro.present || macro.function || macro.count!=1) return 0;
        token=cc_pp_tokens[macro.first];
    }
    return 0;
}
static cc_pp_token cc_pp_condition_token(cc_pp_reader *reader, unsigned *state)
{
    if (*state==2) {
        cc_pp_reader probe=*reader;
        cc_pp_token first=cc_pp_next(&probe);
        *state=0;
        if (first.text<reader->text+reader->size && (first.text[0]=='<' || first.text[0]=='"')) {
            unsigned at=(unsigned)(first.text-reader->text), start=at++;
            unsigned char end=first.text[0]=='<' ? '>' : '"';
            while (at<reader->size && reader->text[at]!=end) {
                if (!reader->text[at] || reader->text[at]=='\n') break;
                ++at;
            }
            if (at==reader->size || reader->text[at]!=end) {
                reader->failed=1; return (cc_pp_token){first.text,0,0,0,0};
            }
            reader->at=at+1;
            return (cc_pp_token){first.text,at+1-start,CC_PP_HEADER,0,first.space};
        }
    }
    cc_pp_token token=cc_pp_next(reader);
    if (*state==1) *state=cc_pp_is(token,"(") ? 2 : 0;
    int query=cc_pp_query_lex_kind(token);
    if (query && query<=2) *state=1;
    return token;
}
static int cc_pp_query_expand(unsigned *cursor, int kind, unsigned depth)
{
    if (depth>=64) return 0;
    if (kind==5) {
        cc_pp_nodes[*cursor].token=(cc_pp_token){(const unsigned char *)"1",1,CC_PP_NUMBER,0,0};
        return 1;
    }
    unsigned current=*cursor, opening=cc_pp_nodes[current].next;
    if (!opening || !cc_pp_is(cc_pp_nodes[opening].token,"(")) return 0;
    unsigned head=0, tail=0, closing=cc_pp_nodes[opening].next, nesting=0;
    while (closing) {
        cc_pp_token token=cc_pp_nodes[closing].token;
        if (cc_pp_is(token,")")) { if (!nesting) break; --nesting; }
        else if (cc_pp_is(token,"(")) ++nesting;
        unsigned node=cc_pp_node_new(token);
        if (!node) { cc_pp_list_release(head); return 0; }
        if (tail) cc_pp_nodes[tail].next=node; else head=node;
        tail=node; closing=cc_pp_nodes[closing].next;
    }
    int success=closing && head;
    if (success && cc_pp_nodes[head].token.kind!=CC_PP_HEADER
        && !cc_pp_is(cc_pp_nodes[head].token,"<")) success=cc_pp_rescan_depth(&head,depth+1);
    unsigned char name[4096]; unsigned size=0; int quote=0, root=-1, found=-1;
    if (success && kind==3) {
        cc_pp_token attribute=cc_pp_nodes[head].token;
        unsigned next=cc_pp_nodes[head].next;
        if (attribute.kind!=CC_PP_IDENT) success=0;
        if (success && next) {
            int scope=cc_pp_is(attribute,"gnu") || cc_pp_is(attribute,"__gnu__");
            if (cc_pp_is(cc_pp_nodes[next].token,"::")) next=cc_pp_nodes[next].next;
            else if (cc_pp_is(cc_pp_nodes[next].token,":")) {
                next=cc_pp_nodes[next].next;
                if (!next || !cc_pp_is(cc_pp_nodes[next].token,":")) success=0;
                else next=cc_pp_nodes[next].next;
            } else success=0;
            if (success && next && !cc_pp_nodes[next].next && cc_pp_nodes[next].token.kind==CC_PP_IDENT) {
                attribute=cc_pp_nodes[next].token;
                if (!scope) attribute=(cc_pp_token){(const unsigned char *)"",0,CC_PP_IDENT,0,0};
            } else success=0;
        }
        if (success && (cc_pp_is(attribute,"packed") || cc_pp_is(attribute,"__packed__")
                     || cc_pp_is(attribute,"aligned") || cc_pp_is(attribute,"__aligned__"))) found=0;
    } else if (success && kind==4) {
        cc_pp_token builtin=cc_pp_nodes[head].token;
        success=builtin.kind==CC_PP_IDENT && !cc_pp_nodes[head].next;
        if (success && (cc_pp_is(builtin,"__builtin_offsetof")
                     || cc_pp_is(builtin,"__builtin_types_compatible_p")
                     || cc_pp_is(builtin,"__builtin_expect")
                     || cc_pp_is(builtin,"__builtin_va_start")
                     || cc_pp_is(builtin,"__builtin_va_copy")
                     || cc_pp_is(builtin,"__builtin_va_end"))) found=0;
    } else if (success) {
        success=cc_pp_header_tokens(head,name,&size,&quote);
        if (success && kind==2 && (cc_pp_current_root>=0 ? (unsigned)cc_pp_current_root+1 : 0)>=cc_file_root_count)
            success=0;
        if (success) found=cc_pp_include_find((cc_file_name){name,size},quote,kind==2,&root);
    }
    cc_pp_list_release(head);
    if (!success) return 0;
    unsigned after=cc_pp_nodes[closing].next;
    cc_pp_nodes[closing].next=0; cc_pp_list_release(opening);
    cc_pp_nodes[current].next=after;
    cc_pp_nodes[current].token=(cc_pp_token){(const unsigned char *)(found>=0 ? "1" : "0"),1,CC_PP_NUMBER,0,0};
    return 1;
}
