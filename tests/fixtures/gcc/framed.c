#include "files.h"
#include "response.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#ifndef __riscv
int cs_read(void *data,unsigned size) { return (int)fread(data,1,size,stdin); }
int cs_write(const void *data,unsigned size) { return (int)fwrite(data,1,size,stdout); }
extern int cs_gcc_finish(int status);
#endif
int main(int argc,char **argv)
{
    assert(argc==3 && !strcmp(argv[0],"cc1") && !strcmp(argv[1],"-E") && !strcmp(argv[2],"in.c"));
    assert(argv[3]==NULL);
    int fd=cs_gcc_fs_open("result",CS_FS_CREATE|CS_FS_WRITE);
    assert(fd>=3 && cs_gcc_fs_write(fd,"copy",4)==4 && cs_gcc_fs_close(fd)==0);
#ifdef __riscv
    assert(fwrite("a\0b",1,3,stdout)==3);
    assert(fputs("warn",stderr)>=0);
    return 0;
#else
    assert(cs_gcc_capture_write(1,"a\0b",3)==3 && cs_gcc_capture_write(2,"warn",4)==4);
    return cs_gcc_finish(0);
#endif
}
