#include "job.h"
#include "files.h"
#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static uint32_t word(const unsigned char *p)
{
    return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}

void cs_gcc_job_release(struct cs_gcc_job *job)
{
    if (!job) return;
    for (int i=0;i<job->argc;++i) free(job->argv[i]);
    free(job->argv); job->argv=NULL; job->argc=0;
}

int cs_gcc_job_decode(unsigned char *packet, size_t size, struct cs_gcc_job *job)
{
    if (!packet || !job || job->argc || job->argv) { errno=EINVAL; return -1; }
    if (size<16 || size>CS_GCC_JOB_MAX || memcmp(packet,"GCCJOB1",8)) {
        errno=EINVAL; return -1;
    }
    uint32_t argc=word(packet+8), files=word(packet+12);
    if (!argc || argc>256 || files>size-16) { errno=EINVAL; return -1; }
    size_t at=16, end=size-files;
    /* Validate all lengths before allocating or changing the mounted files. */
    for (uint32_t i=0;i<argc;++i) {
        if (end-at<4) { errno=EINVAL; return -1; }
        uint32_t length=word(packet+at); at+=4;
        if (length>4096 || length>end-at || (!i && !length)
            || memchr(packet+at,0,length)) { errno=EINVAL; return -1; }
        at+=length;
    }
    if (at!=end) { errno=EINVAL; return -1; }
    struct cs_gcc_job next={0,NULL};
    next.argv=calloc(argc+1,sizeof(*next.argv));
    if (!next.argv) { errno=ENOMEM; return -1; }
    at=16;
    for (uint32_t i=0;i<argc;++i) {
        uint32_t length=word(packet+at); at+=4;
        next.argv[i]=malloc((size_t)length+1);
        if (!next.argv[i]) { cs_gcc_job_release(&next); errno=ENOMEM; return -1; }
        memcpy(next.argv[i],packet+at,length); next.argv[i][length]=0;
        ++next.argc; at+=length;
    }
    if (cs_gcc_fs_mount(packet+end,files)) { cs_gcc_job_release(&next); return -1; }
    *job=next;
    return 0;
}

static int read_exact(int (*reader)(void *, unsigned), unsigned char *data, unsigned size)
{
    while (size) {
        int count=reader(data,size);
        if (count<=0 || (unsigned)count>size) { errno=EIO; return -1; }
        data+=count; size-=(unsigned)count;
    }
    return 0;
}

static int append(int (*reader)(void *, unsigned), unsigned char **packet,
                  unsigned *size, unsigned extra)
{
    if (extra>CS_GCC_JOB_MAX-*size) { errno=EFBIG; return -1; }
    if (!extra) return 0;
    unsigned char *next=realloc(*packet,*size+extra);
    if (!next) { errno=ENOMEM; return -1; }
    *packet=next;
    if (read_exact(reader,next+*size,extra)) return -1;
    *size+=extra;
    return 0;
}

int cs_gcc_job_read(int (*reader)(void *, unsigned), unsigned char **storage,
                    struct cs_gcc_job *job)
{
    if (!reader || !storage || *storage || !job || job->argc || job->argv) {
        errno=EINVAL; return -1;
    }
    unsigned char *packet=NULL;
    unsigned size=0;
    if (append(reader,&packet,&size,16)) goto failed;
    unsigned argc=word(packet+8), files=word(packet+12);
    if (memcmp(packet,"GCCJOB1",8) || !argc || argc>256) { errno=EINVAL; goto failed; }
    for (unsigned i=0;i<argc;++i) {
        if (append(reader,&packet,&size,4)) goto failed;
        unsigned length=word(packet+size-4);
        if (length>4096) { errno=EINVAL; goto failed; }
        if (append(reader,&packet,&size,length)) goto failed;
    }
    if (append(reader,&packet,&size,files) || cs_gcc_job_decode(packet,size,job)) goto failed;
    *storage=packet;
    return 0;
failed:
    free(packet);
    return -1;
}
