#include "files.h"
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef __riscv
#include "copy_space.h"
#endif

static unsigned char bundle[256];
static unsigned used;
static void word(unsigned n)
{
    for (unsigned i=0;i<4;++i) bundle[used++]=(unsigned char)(n>>(8*i));
}
static void input_file(const char *name, const char *data)
{
    word(strlen(name)); word(strlen(data));
    memcpy(bundle+used,name,strlen(name)); used+=strlen(name);
    memcpy(bundle+used,data,strlen(data)); used+=strlen(data);
}
#define CHECK(e) do { if (!(e)) { printf("files-fail:%u\n",(unsigned)__LINE__); fflush(stdout); return 1; } } while (0)

int main(void)
{
    memcpy(bundle,"\0CCFILES1",9); used=9;
    word(2); word(0); word(0);
    input_file("main.c","int main(){return 7;}");
    input_file("include/value.h","abc");
    CHECK(cs_gcc_fs_mount(bundle,used)==0);
    unsigned size,inode,alias; int directory;
    CHECK(cs_gcc_fs_stat("include",&size,&directory,&inode)==0 && directory);
    CHECK(cs_gcc_fs_stat("/",&size,&directory,&alias)==0 && directory && inode!=alias);
    CHECK(cs_gcc_fs_stat("/include/./value.h",&size,&directory,&inode)==0 && !directory && size==3);
    int fd=cs_gcc_fs_open("include/../include/value.h",CS_FS_READ);
    CHECK(fd>=3);
    CHECK(cs_gcc_fs_fstat(fd,&size,&alias)==0 && inode==alias);
    char data[16];
    CHECK(cs_gcc_fs_read(fd,data,2)==2 && !memcmp(data,"ab",2));
    CHECK(cs_gcc_fs_read(fd,data,16)==1 && data[0]=='c');
    CHECK(cs_gcc_fs_read(fd,data,1)==0);
    CHECK(cs_gcc_fs_seek(fd,-2,2)==1 && cs_gcc_fs_read(fd,data,2)==2 && !memcmp(data,"bc",2));
    CHECK(cs_gcc_fs_mount(bundle,used)==-1 && errno==EBUSY);
    CHECK(cs_gcc_fs_write(fd,"x",1)==-1 && errno==EBADF);
    CHECK(cs_gcc_fs_close(fd)==0);
    CHECK(cs_gcc_fs_close(fd)==-1 && errno==EBADF);
    CHECK(cs_gcc_fs_open("include/value.h",CS_FS_WRITE)==-1 && errno==EACCES);
    CHECK(cs_gcc_fs_open("include",CS_FS_READ)==-1 && errno==EISDIR);
    CHECK(cs_gcc_fs_open("../../outside",CS_FS_READ)==-1 && errno==ENOENT);
    fd=cs_gcc_fs_open("result",CS_FS_READ|CS_FS_WRITE|CS_FS_CREATE|CS_FS_EXCL);
    CHECK(fd>=3 && cs_gcc_fs_write(fd,"ab",2)==2);
    CHECK(cs_gcc_fs_seek(fd,4,0)==4 && cs_gcc_fs_write(fd,"Z",1)==1);
    CHECK(cs_gcc_fs_seek(fd,0,0)==0 && cs_gcc_fs_read(fd,data,16)==5 && !memcmp(data,"ab\0\0Z",5));
    CHECK(cs_gcc_fs_seek(fd,INT64_MAX,1)==-1 && errno==EINVAL);
    CHECK(cs_gcc_fs_seek(fd,INT64_MIN,1)==-1 && errno==EINVAL);
    CHECK(cs_gcc_fs_unlink("result")==0);
    CHECK(cs_gcc_fs_stat("result",&size,&directory,&inode)==-1 && errno==ENOENT);
    int other=cs_gcc_fs_open("result",CS_FS_WRITE|CS_FS_CREATE);
    CHECK(other>=3 && cs_gcc_fs_write(other,"new",3)==3);
    CHECK(cs_gcc_fs_seek(fd,0,0)==0 && cs_gcc_fs_read(fd,data,16)==5 && data[4]=='Z');
    CHECK(cs_gcc_fs_close(fd)==0 && cs_gcc_fs_close(other)==0);
    other=cs_gcc_fs_open("result",CS_FS_WRITE|CS_FS_APPEND);
    CHECK(other>=3 && cs_gcc_fs_seek(other,0,0)==0 && cs_gcc_fs_write(other,"!",1)==1);
    CHECK(cs_gcc_fs_close(other)==0);
    const unsigned char *output;
    CHECK(cs_gcc_fs_output("result",&output,&size)==0 && size==4 && !memcmp(output,"new!",4));
    other=cs_gcc_fs_open("result",CS_FS_WRITE|CS_FS_TRUNC);
    CHECK(other>=3 && cs_gcc_fs_close(other)==0);
    CHECK(cs_gcc_fs_output("result",&output,&size)==0 && size==0);
    unsigned char *owned=malloc(4);
    CHECK(owned); memcpy(owned,"take",4);
    CHECK(cs_gcc_fs_replace_owned("missing",owned,4)==-1 && errno==ENOENT);
    CHECK(cs_gcc_fs_replace_owned("main.c",owned,4)==-1 && errno==EACCES);
    CHECK(cs_gcc_fs_replace_owned("result",NULL,4)==-1 && errno==EFAULT);
    CHECK(cs_gcc_fs_replace_owned("result",owned,UINT_MAX)==-1 && errno==EFBIG);
    other=cs_gcc_fs_open("result",CS_FS_READ);
    CHECK(other>=3);
    CHECK(cs_gcc_fs_replace_owned("result",owned,4)==-1 && errno==EBUSY);
    CHECK(cs_gcc_fs_close(other)==0);
    CHECK(cs_gcc_fs_replace_owned("./result",owned,4)==0);
    CHECK(cs_gcc_fs_output("result",&output,&size)==0 && output==owned && size==4);
    CHECK(cs_gcc_fs_replace_owned("result",owned,4)==-1 && errno==EINVAL);
    other=cs_gcc_fs_open("result",CS_FS_READ|CS_FS_WRITE);
    CHECK(other>=3 && cs_gcc_fs_read(other,data,16)==4 && !memcmp(data,"take",4));
    CHECK(cs_gcc_fs_write(other,"!",1)==1 && cs_gcc_fs_close(other)==0);
    CHECK(cs_gcc_fs_output("result",&output,&size)==0 && size==5 && !memcmp(output,"take!",5));
    CHECK(cs_gcc_fs_replace_owned("result",NULL,0)==0);
    CHECK(cs_gcc_fs_output("result",&output,&size)==0 && !output && size==0);
    int handles[61];
    for (unsigned i=0;i<61;++i) { handles[i]=cs_gcc_fs_open("main.c",CS_FS_READ); CHECK(handles[i]>=3); }
    CHECK(cs_gcc_fs_open("main.c",CS_FS_READ)==-1 && errno==EMFILE);
    for (unsigned i=0;i<61;++i) CHECK(cs_gcc_fs_close(handles[i])==0);
    bundle[0]=1;
    CHECK(cs_gcc_fs_mount(bundle,used)==-1 && errno==EINVAL);
    CHECK(cs_gcc_fs_stat("main.c",&size,&directory,&inode)==0);
    bundle[0]=0;
    char *long_name=malloc(4098);
    CHECK(long_name);
    memset(long_name,'a',4096); long_name[4096]=0;
    fd=cs_gcc_fs_open(long_name,CS_FS_CREATE|CS_FS_WRITE);
    CHECK(fd>=3 && cs_gcc_fs_close(fd)==0);
    long_name[4096]='a'; long_name[4097]=0;
    CHECK(cs_gcc_fs_open(long_name,CS_FS_READ)==-1 && errno==ENAMETOOLONG);
    free(long_name);
    CHECK(cs_gcc_fs_mount(bundle,used)==0);
#ifdef __riscv
    FILE *in=fopen("include/value.h","rb");
    CHECK(in && fread(data,1,16,in)==3 && !memcmp(data,"abc",3) && fclose(in)==0);
    FILE *out=fopen("compiled.copy","wb");
    CHECK(out && fwrite("7",1,1,out)==1 && fclose(out)==0);
    CHECK(cs_gcc_fs_output("compiled.copy",&output,&size)==0 && size==1 && output[0]=='7');
#endif
    CHECK(printf("gcc-files:7\n")>0 && fflush(stdout)==0);
    return 0;
}
