#include "job.h"
#include "files.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#ifdef __riscv
#include "copy_space.h"
#else
static unsigned position;
static int cs_read(void *data, unsigned count)
{
    /* Short reads exercise stream assembly as well as the decoder. */
    if (count>3) count=3;
    if (count>69-position) count=69-position;
    extern unsigned char *job_test_input;
    memcpy(data,job_test_input+position,count); position+=count;
    return (int)count;
}
#endif

static unsigned char packet[256];
static unsigned used;
unsigned char *job_test_input=packet;
static void number(unsigned value)
{
    for (unsigned i=0;i<4;++i) packet[used++]=(unsigned char)(value>>(8*i));
}
static void bytes(const char *text, unsigned size)
{
    memcpy(packet+used,text,size); used+=size;
}

int main(void)
{
    bytes("GCCJOB1",8); number(3); number(36);
    number(3); bytes("cc1",3); number(0); number(2); bytes("-E",2);
    bytes("\0CCFILES1",9); number(1); number(0); number(0);
    number(4); number(3); bytes("in.c",4); bytes("a+b",3);
    assert(used==69);
    struct cs_gcc_job job={0,NULL};
    for (unsigned n=0;n<used;++n) {
        assert(cs_gcc_job_decode(packet,n,&job)==-1);
        assert(!job.argc && !job.argv);
    }
    assert(cs_gcc_job_decode(packet,used,&job)==0);
    assert(job.argc==3 && !strcmp(job.argv[0],"cc1") && !strcmp(job.argv[1],""));
    assert(!strcmp(job.argv[2],"-E") && job.argv[3]==NULL);
    assert(cs_gcc_job_decode(packet,used,&job)==-1 && errno==EINVAL);
    cs_gcc_job_release(&job);
    packet[21]=0; /* Embedded NUL in argv[0]. */
    assert(cs_gcc_job_decode(packet,used,&job)==-1 && errno==EINVAL);
    packet[21]='c';
    unsigned size,inode; int directory;
    assert(cs_gcc_fs_stat("in.c",&size,&directory,&inode)==0 && size==3);
    int fd=cs_gcc_fs_open("in.c",CS_FS_READ);
    assert(fd>=3);
    assert(cs_gcc_job_decode(packet,used,&job)==-1 && errno==EBUSY);
    assert(!job.argc && !job.argv);
    assert(cs_gcc_fs_close(fd)==0);
    packet[used-7]=0; /* Invalid mounted name; argv allocation is rolled back. */
    assert(cs_gcc_job_decode(packet,used,&job)==-1);
    assert(!job.argc && !job.argv);
    assert(cs_gcc_fs_stat("in.c",&size,&directory,&inode)==0);
    packet[used-7]='i';
    assert(cs_gcc_job_decode(packet,used,&job)==0);
    cs_gcc_job_release(&job);
    unsigned char *storage=NULL;
    assert(cs_gcc_job_read(cs_read,&storage,&job)==0);
    assert(job.argc==3 && !strcmp(job.argv[2],"-E"));
    fd=cs_gcc_fs_open("in.c",CS_FS_READ);
    char source[4]={0};
    assert(fd>=3 && cs_gcc_fs_read(fd,source,3)==3 && !strcmp(source,"a+b"));
    assert(cs_gcc_fs_close(fd)==0);
    cs_gcc_job_release(&job);
    /* Unmount borrowed storage before releasing it. */
    assert(cs_gcc_fs_mount(packet+33,36)==0);
    free(storage);
    puts("gcc-job:7");
    return 0;
}
