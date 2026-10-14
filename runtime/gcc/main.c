/* This adapter is executed by RV32I copies inside Space. */
#include "copy_space.h"
#include "job.h"
#ifdef CS_GCC_FRAMED_OUTPUT
#include "response.h"
#include "files.h"
#ifdef CS_GCC_COPY_OUTPUT
#include "copy_link.h"
#include <stdint.h>
#include <stdlib.h>
#include <errno.h>
#ifndef CS_GCC_COPY_ADDRESS_BITS
#define CS_GCC_COPY_ADDRESS_BITS 24
#endif
#endif
#endif
#include <stdio.h>
#include <string.h>
extern int __real_main(int argc, char **argv);
static struct cs_gcc_job job;
static unsigned char *packet;
#ifdef CS_GCC_FRAMED_OUTPUT
static const char *output_file;
#ifdef CS_GCC_COPY_OUTPUT
static int copy_output;
static const char *copy_entry="main";
static uint32_t copy_arguments[6];
static unsigned copy_argc;
static int lower_copy(const unsigned char *data, unsigned size)
{
    unsigned char *image=malloc(65536);
    struct cs_copy_link_error error={0,"out of memory"};
    int failed=!image || cs_copy_link_leaf(image,65536,CS_GCC_COPY_ADDRESS_BITS,
        (const char *)data,size,copy_entry,copy_arguments,copy_argc,&error);
    if (!failed) {
        int fd=cs_gcc_fs_open(output_file,CS_FS_WRITE|CS_FS_TRUNC);
        if (fd<0) failed=1;
        else {
            unsigned written=0;
            while (written<65536) {
                int count=cs_gcc_fs_write(fd,image+written,65536-written);
                if (count<=0 || (unsigned)count>65536-written) { failed=1; break; }
                written+=(unsigned)count;
            }
            if (cs_gcc_fs_close(fd)) failed=1;
        }
    }
    free(image);
    if (failed) {
        char message[192];
        int count=snprintf(message,sizeof(message),"gcc: copy lowering line %u: %s\n",
            (unsigned)error.line,error.message ? error.message : "output write failed");
        if (count>0) (void)cs_gcc_capture_write(2,message,
            (unsigned)count<sizeof(message) ? (unsigned)count : sizeof(message)-1);
        return 126;
    }
    return 0;
}
#endif
int cs_gcc_finish(int status)
{
    (void)fflush(NULL);
    if (!status && output_file) {
        const unsigned char *data; unsigned size;
        if (cs_gcc_fs_output(output_file,&data,&size)) {
            const char error[]="gcc: missing output file\n";
            (void)cs_gcc_capture_write(2,error,sizeof(error)-1);
            status=126; output_file=NULL;
        }
#ifdef CS_GCC_COPY_OUTPUT
        else if (copy_output) status=lower_copy(data,size);
#endif
    }
    return cs_gcc_response(status,output_file,cs_write) ? 126 : status;
}
#endif

int __wrap_main(void)
{
    if (cs_gcc_job_read(cs_read,&packet,&job)) {
        fputs("gcc: invalid input job\n",stderr);
        return 125;
    }
#ifdef CS_GCC_FRAMED_OUTPUT
#ifdef CS_GCC_COPY_OUTPUT
    if (job.argc>1 && !strncmp(job.argv[1],"--space-copy=",13)) {
        output_file=job.argv[1]+13;
        if (!*output_file || !strcmp(output_file,"-")) return 125;
        copy_output=1;
        int consumed=2;
        while (consumed<job.argc) {
            const char *option=job.argv[consumed];
            if (!strncmp(option,"--space-entry=",14)) {
                copy_entry=option+14;
                if (!*copy_entry) return 125;
            } else if (!strncmp(option,"--space-arg=",12)) {
                char *end;
                const char *number=option+12;
                if (copy_argc==6 || !*number || *number=='-' || *number=='+' ||
                    *number==' ' || *number=='\t' || *number=='\r' || *number=='\n' ||
                    *number=='\v' || *number=='\f') return 125;
                errno=0;
                unsigned long value=strtoul(number,&end,0);
                if (errno || *end || value>UINT32_MAX) return 125;
                copy_arguments[copy_argc++]=(uint32_t)value;
            } else break;
            ++consumed;
        }
        int remaining=job.argc-consumed;
        memmove(job.argv+1,job.argv+consumed,(size_t)remaining*sizeof(*job.argv));
        job.argc=remaining+1; job.argv[job.argc]=NULL;
    } else
#endif
    if (job.argc>1 && !strncmp(job.argv[1],"--space-result=",15)) {
        output_file=job.argv[1]+15;
        if (!*output_file) { fputs("gcc: empty result path\n",stderr); return 125; }
        for (int i=1;i<job.argc-1;++i) job.argv[i]=job.argv[i+1];
        job.argv[--job.argc]=NULL;
    }
    if (output_file && output_file[0]=='-' && !output_file[1]) output_file=NULL;
#endif
    return __real_main(job.argc,job.argv);
}
