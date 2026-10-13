/* No host filesystem access: all files are views into the IN bundle. */
#define CC_PP_INCLUDE_DEPTH 64
typedef struct {
    cc_pp_reader reader;
    unsigned file, floor;
    int root;
} cc_pp_include_frame;
static cc_pp_include_frame cc_pp_include_stack[CC_PP_INCLUDE_DEPTH];
static unsigned cc_pp_include_depth, cc_pp_current_file;
static int cc_pp_current_root, cc_pp_include_file, cc_pp_include_root;
static unsigned char cc_pp_file_once[CC_FILES_MAX];

static int cc_pp_header_byte(unsigned char *name, unsigned *size, unsigned char byte)
{
    if (*size == 4096 || !byte || byte == '\n') return 0;
    name[(*size)++]=byte;
    return 1;
}
static int cc_pp_header_tokens(unsigned head, unsigned char *name, unsigned *size, int *quote)
{
    *size=0;
    if (!head) return 0;
    cc_pp_token token=cc_pp_nodes[head].token;
    if ((token.kind==CC_PP_LITERAL || token.kind==CC_PP_HEADER) && token.size>=2
        && (token.text[0]=='"' || (token.kind==CC_PP_HEADER && token.text[0]=='<'))
        && token.text[token.size-1]==(token.text[0]=='"' ? '"' : '>') && !cc_pp_nodes[head].next) {
        *quote=token.text[0]=='"';
        for (unsigned i=1;i+1<token.size;++i)
            if (!cc_pp_header_byte(name,size,token.text[i])) return 0;
    } else if (cc_pp_is(token,"<")) {
        *quote=0;
        unsigned node=cc_pp_nodes[head].next;
        while (node && !cc_pp_is(cc_pp_nodes[node].token,">")) {
            token=cc_pp_nodes[node].token;
            if (token.space && !cc_pp_header_byte(name,size,' ')) return 0;
            for (unsigned i=0;i<token.size;++i)
                if (!cc_pp_header_byte(name,size,token.text[i])) return 0;
            node=cc_pp_nodes[node].next;
        }
        if (!node || cc_pp_nodes[node].next) return 0;
    } else return 0;
    return !!*size;
}
static int cc_pp_include_name(cc_pp_reader *reader, unsigned char *name,
                              unsigned *size, int *quote)
{
    *size=0;
    /* Header names are scanned as characters, before ordinary token lexing. */
    unsigned at=reader->at;
    for (;;) {
        while (at<reader->size && (reader->text[at]==' ' || reader->text[at]=='\t'
            || reader->text[at]=='\v' || reader->text[at]=='\f')) ++at;
        if (at+1<reader->size && reader->text[at]=='/' && reader->text[at+1]=='*') {
            at+=2;
            while (at+1<reader->size && !(reader->text[at]=='*' && reader->text[at+1]=='/')) {
                if (!reader->text[at]) return 0;
                ++at;
            }
            if (at+1>=reader->size) return 0;
            at+=2;
        } else break;
    }
    if (at<reader->size && (reader->text[at]=='"' || reader->text[at]=='<')) {
        *quote=reader->text[at]=='"';
        unsigned char end=*quote ? '"' : '>';
        ++at;
        while (at<reader->size && reader->text[at]!=end)
            if (!cc_pp_header_byte(name,size,reader->text[at++])) return 0;
        if (at==reader->size || !*size) return 0;
        reader->at=at+1;
        cc_pp_token tail=cc_pp_next(reader);
        return !reader->failed && (!tail.kind || tail.kind=='\n');
    }
    unsigned head=0, tail=0;
    cc_pp_token token=cc_pp_next(reader);
    while (token.kind && token.kind!='\n' && !reader->failed) {
        unsigned node=cc_pp_node_new(token);
        if (!node) { cc_pp_list_release(head); return 0; }
        if (tail) cc_pp_nodes[tail].next=node; else head=node;
        tail=node; token=cc_pp_next(reader);
    }
    int success=!reader->failed && cc_pp_rescan(&head);
    if (success) success=cc_pp_header_tokens(head,name,size,quote);
    cc_pp_list_release(head);
    return success && *size;
}
static int cc_pp_include_candidate(cc_file_name directory, cc_file_name name)
{
    unsigned char path[8193];
    unsigned size=0, at=0, end=0;
    if (!name.size || name.text[0]=='/' || directory.size+name.size+1>sizeof(path)) return -1;
    for (unsigned i=0;i<directory.size;++i) path[size++]=directory.text[i];
    if (size) path[size++]='/';
    for (unsigned i=0;i<name.size;++i) path[size++]=name.text[i];
    /* Compact path components in place; .. cannot leave the bundle root. */
    while (at<size) {
        unsigned first=at;
        while (at<size && path[at]!='/') ++at;
        unsigned length=at-first; ++at;
        if (!length || (length==1 && path[first]=='.')) continue;
        if (length==2 && path[first]=='.' && path[first+1]=='.') {
            if (!end) return -1;
            while (end && path[end-1]!='/') --end;
            if (end) --end;
        } else {
            if (end) path[end++]='/';
            for (unsigned i=0;i<length;++i) path[end++]=path[first+i];
        }
    }
    cc_file_name candidate={path,end};
    for (unsigned i=0;i<cc_input_file_count;++i)
        if (cc_file_name_equal(candidate,cc_input_files[i].name)) return (int)i;
    return -1;
}
static int cc_pp_include_find(cc_file_name name, int quote, int next, int *root)
{
    int found=-1; *root=-1;
    if (!next && quote && cc_pp_current_file<cc_input_file_count) {
        cc_file_name directory=cc_input_files[cc_pp_current_file].name;
        while (directory.size && directory.text[directory.size-1]!='/') --directory.size;
        if (directory.size) --directory.size;
        found=cc_pp_include_candidate(directory,name);
    }
    for (unsigned i=next && cc_pp_current_root>=0 ? (unsigned)cc_pp_current_root+1 : 0;
         found<0 && i<cc_file_root_count;++i) {
        found=cc_pp_include_candidate(cc_file_roots[i],name);
        if (found>=0) *root=(int)i;
    }
    return found;
}
static int cc_pp_include_directive(cc_pp_reader *reader, int next)
{
    unsigned char bytes[4096]; unsigned size=0; int quote=0, root=-1;
    if (!cc_pp_include_name(reader,bytes,&size,&quote)) return 0;
    int found=cc_pp_include_find((cc_file_name){bytes,size},quote,next,&root);
    if (found<0) return 0;
    if (!cc_pp_file_once[found]) { cc_pp_include_file=found; cc_pp_include_root=root; }
    return 1;
}
static int cc_pp_pragma(cc_pp_reader *reader)
{
    cc_pp_token token=cc_pp_next(reader), tail=cc_pp_next(reader);
    if (!cc_pp_is(token,"once") || reader->failed || (tail.kind && tail.kind!='\n')
        || cc_pp_current_file>=cc_input_file_count) return 0;
    cc_pp_file_once[cc_pp_current_file]=1;
    return 1;
}
