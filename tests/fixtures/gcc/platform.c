#include "files.h"
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/time.h>
#ifndef O_BINARY
#define O_BINARY 0
#endif
int main(void)
{
#ifdef __riscv
    unsigned char packet[]={0,'C','C','F','I','L','E','S','1',1,0,0,0,0,0,0,0,0,0,0,0,
                            1,0,0,0,0,0,0,0,'x'};
    assert(cs_gcc_fs_mount(packet,sizeof(packet))==0);
    assert(access("x",F_OK|R_OK)==0);
    assert(access("x",W_OK)==-1 && errno==EACCES);
    assert(access("x",X_OK)==-1 && errno==EACCES);
    assert(access("missing",R_OK)==-1 && errno==ENOENT);
    assert(access("x",8)==-1 && errno==EINVAL);
    assert(access("/",W_OK|X_OK|R_OK)==0);
    int input=open("x",O_RDONLY|O_NOCTTY|O_BINARY);
    assert(input>=3 && close(input)==0);
    assert(open("x",O_RDONLY|0x40000000)==-1 && errno==EINVAL);
    int fd=cs_gcc_fs_open("out",CS_FS_CREATE|CS_FS_WRITE); assert(fd>=3);
    assert(cs_gcc_fs_close(fd)==0 && access("out",W_OK|R_OK)==0);
    assert(sysconf(_SC_PAGESIZE)==4096);
    assert(sysconf(_SC_PHYS_PAGES)==CS_GCC_MEMORY_BYTES/4096);
    long available=sysconf(_SC_AVPHYS_PAGES); assert(available>0 && available<=sysconf(_SC_PHYS_PAGES));
    assert(sysconf(_SC_OPEN_MAX)==64 && sysconf(_SC_CLK_TCK)==100);
    assert(sysconf(-1)==-1 && errno==EINVAL);
    struct timeval first,second;
    assert(gettimeofday(&first,NULL)==0 && gettimeofday(&second,NULL)==0);
    assert(second.tv_sec*1000000+second.tv_usec==first.tv_sec*1000000+first.tv_usec+1);
    extern int _gettimeofday(struct timeval *,void *);
    assert(_gettimeofday(NULL,NULL)==-1 && errno==EFAULT);
    assert(_gettimeofday(&first,&second)==-1 && errno==EINVAL);
#endif
    puts("gcc-platform:7"); return 0;
}
