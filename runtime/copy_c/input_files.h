#ifndef COPY_C_INPUT_FILES_H
#define COPY_C_INPUT_FILES_H
#define CC_FILES_MAX 1024
#define CC_FILE_ROOTS_MAX 32
typedef struct { const unsigned char *text; unsigned size; } cc_file_name;
typedef struct { cc_file_name name; unsigned char *data; unsigned size; } cc_input_file;
static cc_input_file cc_input_files[CC_FILES_MAX];
static cc_file_name cc_file_roots[CC_FILE_ROOTS_MAX];
static unsigned cc_input_file_count, cc_file_root_count, cc_main_file;
static int cc_files_magic(const unsigned char *data, unsigned size)
{
    static const unsigned char magic[9]={0,'C','C','F','I','L','E','S','1'};
    if (size<9) return 0;
    for (unsigned i=0;i<9;++i) if (data[i]!=magic[i]) return 0;
    return 1;
}
static int cc_file_name_valid(cc_file_name name, int root)
{
    if (!name.size) return root;
    if (name.size>4096 || name.text[0]=='/' || name.text[name.size-1]=='/') return 0;
    unsigned first=0;
    for (unsigned i=0;i<=name.size;++i) {
        if (i<name.size && !name.text[i]) return 0;
        if (i==name.size || name.text[i]=='/') {
            unsigned count=i-first;
            if (!count || (count==1 && name.text[first]=='.')
                || (count==2 && name.text[first]=='.' && name.text[first+1]=='.')) return 0;
            first=i+1;
        }
    }
    return 1;
}
static int cc_file_name_equal(cc_file_name left, cc_file_name right)
{
    if (left.size!=right.size) return 0;
    for (unsigned i=0;i<left.size;++i) if (left.text[i]!=right.text[i]) return 0;
    return 1;
}
static int cc_files_word(const unsigned char *data, unsigned size, unsigned *at, unsigned *value)
{
    if (*at>size || size-*at<4) return 0;
    *value=0;
    for (unsigned i=0;i<4;++i) *value|=(unsigned)data[(*at)++]<<(i*8);
    return 1;
}
static int cc_files_decode(unsigned char *data, unsigned size)
{
    unsigned at=9, count, main, roots, unique_roots=0;
    cc_input_file_count=cc_file_root_count=cc_main_file=0;
    if (!cc_files_magic(data,size) || !cc_files_word(data,size,&at,&count)
        || !cc_files_word(data,size,&at,&main) || !cc_files_word(data,size,&at,&roots)) return 0;
    if (!count || count>CC_FILES_MAX || main>=count || roots>CC_FILE_ROOTS_MAX) return 0;
    for (unsigned i=0;i<roots;++i) {
        unsigned length;
        if (!cc_files_word(data,size,&at,&length) || length>size-at) return 0;
        cc_file_name name={data+at,length}; at+=length;
        if (!cc_file_name_valid(name,1)) return 0;
        unsigned j=0;
        while (j<unique_roots && !cc_file_name_equal(name,cc_file_roots[j])) ++j;
        if (j==unique_roots) cc_file_roots[unique_roots++]=name;
    }
    for (unsigned i=0;i<count;++i) {
        unsigned length, bytes;
        if (!cc_files_word(data,size,&at,&length) || !cc_files_word(data,size,&at,&bytes)
            || length>size-at) return 0;
        cc_input_files[i].name=(cc_file_name){data+at,length}; at+=length;
        if (!cc_file_name_valid(cc_input_files[i].name,0) || bytes>size-at) return 0;
        for (unsigned j=0;j<i;++j)
            if (cc_file_name_equal(cc_input_files[i].name,cc_input_files[j].name)) return 0;
        cc_input_files[i].data=data+at; cc_input_files[i].size=bytes; at+=bytes;
    }
    if (at!=size) return 0;
    cc_input_file_count=count; cc_file_root_count=unique_roots; cc_main_file=main;
    return 1;
}
#endif
