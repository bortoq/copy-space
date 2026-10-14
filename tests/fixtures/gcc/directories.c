#include "include/dirent.h"
#include "files.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
static unsigned char packet[256];
static unsigned at;
static void number(unsigned n) { for (unsigned i=0;i<4;++i) packet[at++]=(unsigned char)(n>>(8*i)); }
static void item(const char *name)
{
    unsigned size=(unsigned)strlen(name); number(size); number(0);
    memcpy(packet+at,name,size); at+=size;
}
int main(void)
{
    memcpy(packet,"\0CCFILES1",9); at=9;
    number(4); number(0); number(0);
    item("inc/sub/a.h"); item("inc/sub/b.h"); item("inc/top.h"); item("main.c");
    assert(cs_gcc_fs_mount(packet,at)==0);
    DIR *root=opendir("/"); assert(root);
    struct dirent *d=readdir(root); assert(d && !strcmp(d->d_name,"inc") && d->d_type==DT_DIR);
    unsigned size,inode; int directory;
    assert(cs_gcc_fs_stat("inc",&size,&directory,&inode)==0 && d->d_ino==inode);
    d=readdir(root); assert(d && !strcmp(d->d_name,"main.c") && d->d_type==DT_REG);
    errno=0; assert(!readdir(root) && !errno);
    assert(cs_gcc_fs_mount(packet,at)==-1 && errno==EBUSY);
    assert(closedir(root)==0);
    assert(!opendir("main.c") && errno==ENOTDIR);
    assert(!opendir("absent") && errno==ENOENT);
    DIR *inc=opendir("/inc/./"); assert(inc);
    d=readdir(inc); assert(d && !strcmp(d->d_name,"sub"));
    long position=telldir(inc); assert(position>0);
    d=readdir(inc); assert(d && !strcmp(d->d_name,"top.h"));
    assert(!readdir(inc));
    seekdir(inc,position); d=readdir(inc); assert(d && !strcmp(d->d_name,"top.h"));
    rewinddir(inc); d=readdir(inc); assert(d && !strcmp(d->d_name,"sub"));
    assert(closedir(inc)==0);
    DIR *sub=opendir("inc/sub"); assert(sub);
    d=readdir(sub); assert(d && !strcmp(d->d_name,"a.h"));
    assert(cs_gcc_fs_stat("inc/sub/a.h",&size,&directory,&inode)==0 && inode==d->d_ino);
    d=readdir(sub); assert(d && !strcmp(d->d_name,"b.h"));
    assert(!readdir(sub)); assert(closedir(sub)==0);
    int fd=cs_gcc_fs_open("new/x",CS_FS_CREATE|CS_FS_WRITE); assert(fd>=3);
    assert(cs_gcc_fs_close(fd)==0);
    DIR *created=opendir("new"); assert(created);
    d=readdir(created); assert(d && !strcmp(d->d_name,"x") && d->d_type==DT_REG);
    assert(!readdir(created)); assert(closedir(created)==0);
    assert(closedir(NULL)==-1 && errno==EINVAL);
    unsigned cursor=0; char small[1];
    assert(cs_gcc_fs_directory_next("inc",&cursor,small,sizeof(small),&inode,&directory)==-1);
    assert(errno==ERANGE && cursor==0);
    assert(cs_gcc_fs_mount(packet,at)==0);
    puts("gcc-directories:7"); return 0;
}
