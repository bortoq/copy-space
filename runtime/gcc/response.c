#include "response.h"
#include "files.h"
#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#define CAPTURE_LIMIT (16u*1024u*1024u)
struct captured { unsigned char *data; unsigned size,capacity; };
static struct captured streams[2];

void cs_gcc_capture_reset(void)
{
    for (unsigned i=0;i<2;++i) { free(streams[i].data); streams[i]=(struct captured){0}; }
}

int cs_gcc_capture_write(int fd, const void *data, size_t size)
{
    if (fd!=1 && fd!=2) { errno=EBADF; return -1; }
    if (size && !data) { errno=EFAULT; return -1; }
    unsigned total=streams[0].size+streams[1].size;
    if (size>CAPTURE_LIMIT-total) { errno=EFBIG; return -1; }
    struct captured *stream=streams+(fd-1);
    unsigned required=stream->size+(unsigned)size;
    if (required>stream->capacity) {
        unsigned capacity=stream->capacity ? stream->capacity : 256;
        while (capacity<required) capacity*=2;
        unsigned char *next=realloc(stream->data,capacity);
        if (!next) { errno=ENOMEM; return -1; }
        stream->data=next; stream->capacity=capacity;
    }
    if (size) memcpy(stream->data+stream->size,data,size);
    stream->size=required;
    return (int)size;
}

static int send(int (*writer)(const void *,unsigned), const unsigned char *data, unsigned size)
{
    while (size) {
        int count=writer(data,size);
        if (count<=0 || (unsigned)count>size) { errno=EIO; return -1; }
        data+=count; size-=(unsigned)count;
    }
    return 0;
}

static void word(unsigned char *data, uint32_t value)
{
    for (unsigned i=0;i<4;++i) data[i]=(unsigned char)(value>>(8*i));
}

int cs_gcc_response(int status, const char *output_file, int (*writer)(const void *,unsigned))
{
    if (!writer) { errno=EINVAL; return -1; }
    const unsigned char *file=NULL; unsigned size=0;
    if (!status && output_file && cs_gcc_fs_output(output_file,&file,&size)) return -1;
    unsigned char header[24]; memcpy(header,"GCCOUT1",8);
    word(header+8,(uint32_t)status);
    word(header+12,streams[0].size); word(header+16,streams[1].size); word(header+20,size);
    if (send(writer,header,sizeof(header)) || send(writer,streams[0].data,streams[0].size)
        || send(writer,streams[1].data,streams[1].size) || send(writer,file,size)) return -1;
    return 0;
}
