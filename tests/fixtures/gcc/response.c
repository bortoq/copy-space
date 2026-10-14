#include "response.h"
#include "files.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
static unsigned char output[512];
static unsigned used;
static int writer(const void *data, unsigned size)
{
    if (size>3) size=3;
    assert(size<=sizeof(output)-used);
    memcpy(output+used,data,size); used+=size; return (int)size;
}
static int failed_writer(const void *data, unsigned size) { (void)data; (void)size; return 0; }
static unsigned word(unsigned at)
{
    return (unsigned)output[at]|(unsigned)output[at+1]<<8|(unsigned)output[at+2]<<16|(unsigned)output[at+3]<<24;
}
int main(void)
{
    unsigned char packet[]={0,'C','C','F','I','L','E','S','1',1,0,0,0,0,0,0,0,0,0,0,0,
                            1,0,0,0,0,0,0,0,'x'};
    assert(cs_gcc_fs_mount(packet,sizeof(packet))==0);
    int fd=cs_gcc_fs_open("result",CS_FS_CREATE|CS_FS_WRITE);
    assert(fd>=3 && cs_gcc_fs_write(fd,"copy",4)==4 && cs_gcc_fs_close(fd)==0);
    assert(cs_gcc_capture_write(1,"a\0b",3)==3);
    assert(cs_gcc_capture_write(2,"error",5)==5);
    assert(cs_gcc_capture_write(3,"x",1)==-1 && errno==EBADF);
    assert(cs_gcc_capture_write(1,NULL,1)==-1 && errno==EFAULT);
    assert(cs_gcc_capture_write(1,"x",16u*1024u*1024u)==-1 && errno==EFBIG);
    assert(cs_gcc_response(0,"result",writer)==0);
    assert(used==36 && !memcmp(output,"GCCOUT1",8));
    assert(word(8)==0 && word(12)==3 && word(16)==5 && word(20)==4);
    assert(!memcmp(output+24,"a\0berrorcopy",12));
    struct cs_gcc_result result={0};
    assert(cs_gcc_response_decode(output,used,&result)==0);
    assert(result.status==0 && result.out_size==3 && result.err_size==5 && result.file_size==4);
    assert(!memcmp(result.out,"a\0b",3) && !memcmp(result.err,"error",5) && !memcmp(result.file,"copy",4));
    unsigned char saved[sizeof(result)]; memcpy(saved,&result,sizeof(result));
    for (unsigned n=0;n<used;++n) {
        assert(cs_gcc_response_decode(output,n,&result)==-1 && errno==EINVAL);
        assert(!memcmp(saved,&result,sizeof(result)));
    }
    unsigned char old=output[12]; output[12]=255;
    assert(cs_gcc_response_decode(output,used,&result)==-1); output[12]=old;
    output[8]=1; assert(cs_gcc_response_decode(output,used,&result)==-1); output[8]=0;
    output[used]=0; assert(cs_gcc_response_decode(output,used+1,&result)==-1);
    used=0;
    assert(cs_gcc_response(1,"missing",writer)==0);
    assert(word(8)==1 && word(20)==0 && used==32);
    assert(cs_gcc_response(0,"missing",writer)==-1 && errno==ENOENT);
    assert(cs_gcc_response(0,NULL,failed_writer)==-1 && errno==EIO);
    cs_gcc_capture_reset(); used=0;
    assert(cs_gcc_response(0,NULL,writer)==0 && used==24 && word(12)==0 && word(16)==0);
    puts("gcc-response:7"); return 0;
}
