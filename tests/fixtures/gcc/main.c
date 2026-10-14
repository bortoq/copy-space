#include "files.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#ifndef __riscv
/* Only channel transport is native here; files remain in guest-library memory. */
int cs_read(void *data, unsigned size) { return (int)fread(data,1,size,stdin); }
#endif
int main(int argc, char **argv)
{
    assert(argc==3 && !strcmp(argv[0],"cc1") && !strcmp(argv[1],"-E"));
    assert(!strcmp(argv[2],"in.c") && argv[3]==NULL);
    int fd=cs_gcc_fs_open(argv[2],CS_FS_READ);
    char text[4]={0};
    assert(fd>=3 && cs_gcc_fs_read(fd,text,3)==3 && !strcmp(text,"a+b"));
    assert(cs_gcc_fs_close(fd)==0);
    puts("gcc-main:7");
    return 0;
}
