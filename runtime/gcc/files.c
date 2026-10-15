#include "files.h"
#include <errno.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include "../copy_c/input_files.h"

#define FD_COUNT 64
#define PATH_BYTES 4097
typedef struct {
    char *name;
    unsigned char *data;
    unsigned size, capacity, references;
    int readonly, linked;
} file;
typedef struct { file *object; unsigned position, flags; } descriptor;
static file objects[CC_FILES_MAX];
static descriptor handles[FD_COUNT];
static char *directories[CC_FILES_MAX];
static unsigned open_directories;
static int failure(int code) { errno=code; return -1; }

static int normalize(const char *path, char *out)
{
    unsigned used=0;
    if (!path || !*path) return failure(ENOENT);
    while (*path) {
        while (*path=='/') ++path;
        const char *first=path;
        while (*path && *path!='/') ++path;
        size_t length=(size_t)(path-first);
        if (!length || (length==1 && first[0]=='.')) continue;
        if (length==2 && first[0]=='.' && first[1]=='.') {
            if (!used) return failure(ENOENT);
            while (used && out[used-1]!='/') --used;
            if (used) --used;
            continue;
        }
        unsigned separator=used!=0;
        if (used>PATH_BYTES-1-separator || length>PATH_BYTES-1-used-separator)
            return failure(ENAMETOOLONG);
        if (used) out[used++]='/';
        memcpy(out+used,first,length); used+=(unsigned)length;
    }
    out[used]=0;
    return 0;
}

static file *lookup(const char *name)
{
    for (unsigned i=0;i<CC_FILES_MAX;++i)
        if (objects[i].name && objects[i].linked && !strcmp(objects[i].name,name)) return objects+i;
    return NULL;
}

static void release(file *object)
{
    free(object->name);
    if (!object->readonly) free(object->data);
    memset(object,0,sizeof(*object));
}

int cs_gcc_fs_mount(unsigned char *blob, unsigned size)
{
    if (open_directories) return failure(EBUSY);
    for (unsigned i=3;i<FD_COUNT;++i) if (handles[i].object) return failure(EBUSY);
    if (!cc_files_decode(blob,size)) return failure(EINVAL);
    for (unsigned i=0;i<cc_input_file_count;++i)
        if (cc_input_files[i].size>INT_MAX) return failure(EFBIG);
    char **names=calloc(cc_input_file_count,sizeof(*names));
    if (!names && cc_input_file_count) return failure(ENOMEM);
    unsigned i;
    for (i=0;i<cc_input_file_count;++i) {
        unsigned count=cc_input_files[i].name.size;
        names[i]=malloc((size_t)count+1);
        if (!names[i]) break;
        memcpy(names[i],cc_input_files[i].name.text,count); names[i][count]=0;
    }
    if (i!=cc_input_file_count) {
        while (i) free(names[--i]);
        free(names); return failure(ENOMEM);
    }
    for (i=0;i<CC_FILES_MAX;++i) if (objects[i].name) release(objects+i);
    for (i=0;i<CC_FILES_MAX;++i) { free(directories[i]); directories[i]=NULL; }
    for (i=0;i<cc_input_file_count;++i)
        objects[i]=(file){names[i],cc_input_files[i].data,cc_input_files[i].size,
                         cc_input_files[i].size,0,1,1};
    free(names); return 0;
}

static int directory_inode(const char *name, unsigned *inode)
{
    for (unsigned i=0;i<CC_FILES_MAX;++i)
        if (directories[i] && !strcmp(directories[i],name)) {
            *inode=CC_FILES_MAX+1+i; return 0;
        }
    for (unsigned i=0;i<CC_FILES_MAX;++i) if (!directories[i]) {
        directories[i]=malloc(strlen(name)+1);
        if (!directories[i]) return failure(ENOMEM);
        strcpy(directories[i],name); *inode=CC_FILES_MAX+1+i; return 0;
    }
    return failure(ENFILE);
}

int cs_gcc_fs_stat(const char *path, unsigned *size, int *directory, unsigned *inode)
{
    char name[PATH_BYTES];
    if (normalize(path,name)) return -1;
    file *object=lookup(name);
    if (object) { *size=object->size; *directory=0; *inode=(unsigned)(object-objects)+1; return 0; }
    size_t length=strlen(name);
    if (!length) { *size=0; *directory=1; return directory_inode(name,inode); }
    for (unsigned i=0;i<CC_FILES_MAX;++i) {
        const char *p=objects[i].name;
        if (p && objects[i].linked && !strncmp(p,name,length) && p[length]=='/') {
            *size=0; *directory=1; return directory_inode(name,inode);
        }
    }
    return failure(ENOENT);
}

int cs_gcc_fs_open(const char *path, unsigned flags)
{
    const unsigned allowed=CS_FS_READ|CS_FS_WRITE|CS_FS_CREATE|CS_FS_TRUNC|CS_FS_APPEND|CS_FS_EXCL;
    if ((flags & ~allowed) || !(flags & (CS_FS_READ|CS_FS_WRITE))) return failure(EINVAL);
    if ((flags & (CS_FS_TRUNC|CS_FS_APPEND)) && !(flags & CS_FS_WRITE)) return failure(EINVAL);
    char name[PATH_BYTES];
    if (normalize(path,name)) return -1;
    unsigned ignored, inode; int directory;
    if (!cs_gcc_fs_stat(path,&ignored,&directory,&inode) && directory) return failure(EISDIR);
    file *object=lookup(name);
    if (object && (flags & CS_FS_CREATE) && (flags & CS_FS_EXCL)) return failure(EEXIST);
    if (object && object->readonly && (flags & CS_FS_WRITE)) return failure(EACCES);
    if (!object && !(flags & CS_FS_CREATE)) return failure(ENOENT);
    unsigned fd;
    for (fd=3;fd<FD_COUNT && handles[fd].object;++fd) {}
    if (fd==FD_COUNT) return failure(EMFILE);
    if (!object) {
        for (unsigned i=0;i<CC_FILES_MAX;++i) if (!objects[i].name) { object=objects+i; break; }
        if (!object) return failure(ENFILE);
        object->name=malloc(strlen(name)+1);
        if (!object->name) return failure(ENOMEM);
        strcpy(object->name,name); object->linked=1;
    }
    if (flags & CS_FS_TRUNC) object->size=0;
    ++object->references;
    handles[fd]=(descriptor){object,0,flags}; return (int)fd;
}

static descriptor *get(int fd)
{
    if (fd<3 || fd>=FD_COUNT || !handles[fd].object) { errno=EBADF; return NULL; }
    return handles+fd;
}

int cs_gcc_fs_close(int fd)
{
    descriptor *handle=get(fd); if (!handle) return -1;
    file *object=handle->object;
    memset(handle,0,sizeof(*handle)); --object->references;
    if (!object->linked && !object->references) release(object);
    return 0;
}

int cs_gcc_fs_read(int fd, void *data, size_t size)
{
    descriptor *handle=get(fd); if (!handle) return -1;
    if (!(handle->flags & CS_FS_READ)) return failure(EBADF);
    if (size>INT_MAX) return failure(EINVAL);
    if (size && !data) return failure(EFAULT);
    unsigned left=handle->position<handle->object->size ? handle->object->size-handle->position : 0;
    unsigned count=size<left ? (unsigned)size : left;
    if (count) memcpy(data,handle->object->data+handle->position,count);
    handle->position+=count; return (int)count;
}

int cs_gcc_fs_write(int fd, const void *data, size_t size)
{
    descriptor *handle=get(fd); if (!handle) return -1;
    if (!(handle->flags & CS_FS_WRITE)) return failure(EBADF);
    if (size>INT_MAX) return failure(EINVAL);
    if (size && !data) return failure(EFAULT);
    if (!size) return 0;
    file *object=handle->object;
    unsigned position=(handle->flags & CS_FS_APPEND) ? object->size : handle->position;
    if (size>(unsigned)INT_MAX-position) return failure(EFBIG);
    unsigned end=position+(unsigned)size;
    if (end>object->capacity) {
        unsigned char *grown=realloc(object->data,end);
        if (!grown) return failure(ENOMEM);
        object->data=grown; object->capacity=end;
    }
    if (position>object->size) memset(object->data+object->size,0,position-object->size);
    memcpy(object->data+position,data,size);
    if (end>object->size) object->size=end;
    handle->position=end; return (int)size;
}

int cs_gcc_fs_seek(int fd, int64_t offset, int origin)
{
    descriptor *handle=get(fd); if (!handle) return -1;
    int64_t base;
    if (origin==0) base=0;
    else if (origin==1) base=handle->position;
    else if (origin==2) base=handle->object->size;
    else return failure(EINVAL);
    if (base<0 || offset < -base || offset > INT_MAX-base) return failure(EINVAL);
    handle->position=(unsigned)(base+offset); return (int)handle->position;
}

int cs_gcc_fs_fstat(int fd, unsigned *size, unsigned *inode)
{
    descriptor *handle=get(fd); if (!handle) return -1;
    *size=handle->object->size; *inode=(unsigned)(handle->object-objects)+1; return 0;
}

int cs_gcc_fs_unlink(const char *path)
{
    char name[PATH_BYTES]; if (normalize(path,name)) return -1;
    file *object=lookup(name); if (!object) return failure(ENOENT);
    if (object->readonly) return failure(EACCES);
    object->linked=0;
    if (!object->references) release(object);
    return 0;
}

int cs_gcc_fs_output(const char *path, const unsigned char **data, unsigned *size)
{
    char name[PATH_BYTES]; if (normalize(path,name)) return -1;
    file *object=lookup(name); if (!object) return failure(ENOENT);
    *data=object->data; *size=object->size; return 0;
}

int cs_gcc_fs_replace_owned(const char *path, unsigned char *data, unsigned size)
{
    if (size>INT_MAX) return failure(EFBIG);
    if (size && !data) return failure(EFAULT);
    char name[PATH_BYTES]; if (normalize(path,name)) return -1;
    file *object=lookup(name); if (!object) return failure(ENOENT);
    if (object->readonly) return failure(EACCES);
    if (object->references) return failure(EBUSY);
    if (data && data==object->data) return failure(EINVAL);
    free(object->data);
    object->data=data; object->size=size; object->capacity=size;
    return 0;
}

int cs_gcc_fs_directory_open(const char *path)
{
    unsigned size,inode; int directory;
    if (cs_gcc_fs_stat(path,&size,&directory,&inode)) return -1;
    if (!directory) return failure(ENOTDIR);
    if (open_directories==UINT_MAX) return failure(EMFILE);
    ++open_directories; return 0;
}
int cs_gcc_fs_access(const char *path, int write, int execute)
{
    unsigned size,inode; int directory;
    if (cs_gcc_fs_stat(path,&size,&directory,&inode)) return -1;
    if (directory) return 0;
    char name[PATH_BYTES]; if (normalize(path,name)) return -1;
    file *object=lookup(name);
    if (execute || (write && object->readonly)) return failure(EACCES);
    return 0;
}
void cs_gcc_fs_directory_close(void) { if (open_directories) --open_directories; }

static const char *child(const file *object, const char *base, unsigned length)
{
    if (!object->name || !object->linked) return NULL;
    if (!length) return object->name;
    if (strncmp(object->name,base,length) || object->name[length]!='/') return NULL;
    return object->name+length+1;
}

int cs_gcc_fs_directory_next(const char *path, unsigned *cursor, char *name,
                            unsigned capacity, unsigned *inode, int *directory)
{
    if (!cursor || !name || !inode || !directory || *cursor>CC_FILES_MAX) return failure(EINVAL);
    char base[PATH_BYTES]; if (normalize(path,base)) return -1;
    unsigned length=(unsigned)strlen(base);
    for (unsigned i=*cursor;i<CC_FILES_MAX;++i) {
        const char *part=child(objects+i,base,length);
        if (!part || !*part) continue;
        unsigned bytes=0; while (part[bytes] && part[bytes]!='/') ++bytes;
        int duplicate=0;
        for (unsigned j=0;j<i;++j) {
            const char *previous=child(objects+j,base,length);
            if (previous && !strncmp(previous,part,bytes)
                && (!previous[bytes] || previous[bytes]=='/')) { duplicate=1; break; }
        }
        if (duplicate) continue;
        if (bytes>=capacity) return failure(ERANGE);
        memcpy(name,part,bytes); name[bytes]=0;
        *directory=part[bytes]=='/';
        if (*directory) {
            char full[PATH_BYTES];
            memcpy(full,base,length);
            unsigned at=length; if (at) full[at++]='/';
            memcpy(full+at,name,bytes+1);
            if (directory_inode(full,inode)) return -1;
        } else *inode=i+1;
        *cursor=i+1; return 1;
    }
    *cursor=CC_FILES_MAX; return 0;
}
