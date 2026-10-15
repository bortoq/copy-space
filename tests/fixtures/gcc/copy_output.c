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
/* Mock cc1 output: this fixture proves the adapter, not C compilation. */
int main(int argc,char **argv)
{
    assert(argc==3 && !strcmp(argv[0],"cc1") && !strcmp(argv[1],"-S") && !strcmp(argv[2],"in.s"));
    assert(argv[3]==NULL);
    int input=cs_gcc_fs_open("in.s",CS_FS_READ);
    assert(input>=3);
    char assembly[8192];
    int size=cs_gcc_fs_read(input,assembly,sizeof(assembly));
    assert(size>=0 && cs_gcc_fs_close(input)==0);
    int fd=cs_gcc_fs_open("result.s",CS_FS_CREATE|CS_FS_WRITE|CS_FS_TRUNC);
    assert(fd>=3 && cs_gcc_fs_write(fd,assembly,(unsigned)size)==size && cs_gcc_fs_close(fd)==0);
#ifdef __riscv
    return 0;
#else
    return cs_gcc_finish(0);
#endif
}
