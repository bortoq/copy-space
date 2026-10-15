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
#ifndef CS_GCC_COPY_PROGRAM_BYTES
#define CS_GCC_COPY_PROGRAM_BYTES 262144
#endif
#if CS_GCC_COPY_PROGRAM_BYTES < 262144 || CS_GCC_COPY_PROGRAM_BYTES > 268435456 || \
    (CS_GCC_COPY_PROGRAM_BYTES & (CS_GCC_COPY_PROGRAM_BYTES-1))
#error "copy program size must be a power of two in 262144..268435456"
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
static int copy_program;
static const char *copy_entry="main";
static uint32_t copy_arguments[6];
static unsigned copy_argc;
static uint32_t copy_memory_bytes=8192;
static const char *copy_objects[7];
static unsigned copy_objectc;
static const char *copy_library;
static int copy_no_libgcc;
/* Optional read-only target runtime installed while preparing the image. */
extern const unsigned char cs_gcc_default_archive[] __attribute__((weak));
extern const unsigned cs_gcc_default_archive_size __attribute__((weak));
static int copy_number(const char *number, uint32_t *result)
{
    char *end;
    if (!*number || *number=='-' || *number=='+' ||
        *number==' ' || *number=='\t' || *number=='\r' || *number=='\n' ||
        *number=='\v' || *number=='\f') return -1;
    errno=0;
    unsigned long value=strtoul(number,&end,0);
    if (errno || *end || value>UINT32_MAX) return -1;
    *result=(uint32_t)value;
    return 0;
}
static int lower_copy(const unsigned char *data, unsigned size)
{
    unsigned image_bytes=copy_program ? CS_GCC_COPY_PROGRAM_BYTES : 65536;
    unsigned char *image=malloc(image_bytes);
    struct cs_copy_link_error error={0,"out of memory"};
    int failed=!image;
    struct cs_copy_archive archives[2];unsigned archive_count=0;
    if (copy_library) {
        const unsigned char *archive;unsigned bytes;
        if (cs_gcc_fs_output(copy_library,&archive,&bytes)) {
            error.message="missing copy library file";failed=1;
        } else archives[archive_count++]=(struct cs_copy_archive){bytes ? (const char *)archive : "",bytes};
    }
    if (copy_program && !copy_no_libgcc && cs_gcc_default_archive && &cs_gcc_default_archive_size)
        archives[archive_count++]=(struct cs_copy_archive){(const char *)cs_gcc_default_archive,cs_gcc_default_archive_size};
    if (image && !failed) {
        if (copy_objectc || archive_count) {
            struct cs_copy_object objects[8]={{size ? (const char *)data : "",size}};
            for (unsigned i=0;i<copy_objectc;++i) {
                const unsigned char *source;unsigned bytes;
                if (cs_gcc_fs_output(copy_objects[i],&source,&bytes)) {
                    error.message="missing copy object file";failed=1;break;
                }
                objects[i+1]=(struct cs_copy_object){bytes ? (const char *)source : "",bytes};
            }
            if (!failed && archive_count) {
                failed=cs_copy_link_archives_alloc(image,image_bytes,CS_GCC_COPY_ADDRESS_BITS,
                    copy_memory_bytes,objects,copy_objectc+1,archives,archive_count,
                    copy_entry,copy_arguments,copy_argc,&error);
            } else if (!failed) failed=cs_copy_link_objects_alloc(image,image_bytes,CS_GCC_COPY_ADDRESS_BITS,
                copy_memory_bytes,objects,copy_objectc+1,copy_entry,copy_arguments,copy_argc,&error);
        } else failed=copy_program ? cs_copy_link_program_memory(image,image_bytes,CS_GCC_COPY_ADDRESS_BITS,
            copy_memory_bytes,(const char *)data,size,copy_entry,copy_arguments,copy_argc,&error) :
            cs_copy_link_leaf(image,image_bytes,CS_GCC_COPY_ADDRESS_BITS,
            (const char *)data,size,copy_entry,copy_arguments,copy_argc,&error);
    }
    if (!failed) {
        failed=cs_gcc_fs_replace_owned(output_file,image,image_bytes);
        if (!failed) image=NULL;
        else error.message="output replacement failed";
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
    if (job.argc>1 && (!strncmp(job.argv[1],"--space-copy=",13) ||
                      !strncmp(job.argv[1],"--space-program=",16))) {
        copy_program=!strncmp(job.argv[1],"--space-program=",16);
        output_file=job.argv[1]+(copy_program ? 16 : 13);
        if (!*output_file || !strcmp(output_file,"-")) return 125;
        copy_output=1;
        int consumed=2;
        while (consumed<job.argc) {
            const char *option=job.argv[consumed];
            if (!strncmp(option,"--space-entry=",14)) {
                copy_entry=option+14;
                if (!*copy_entry) return 125;
            } else if (!strncmp(option,"--space-arg=",12)) {
                if (copy_argc==6 || copy_number(option+12,&copy_arguments[copy_argc])) return 125;
                ++copy_argc;
            } else if (!strncmp(option,"--space-memory=",15)) {
                if (!copy_program || copy_number(option+15,&copy_memory_bytes) ||
                    copy_memory_bytes<8192 || copy_memory_bytes>=CS_GCC_COPY_PROGRAM_BYTES ||
                    (copy_memory_bytes&(copy_memory_bytes-1))) return 125;
            } else if (!strncmp(option,"--space-object=",15)) {
                if (!copy_program || copy_objectc==7 || !option[15]) return 125;
                copy_objects[copy_objectc++]=option+15;
            } else if (!strncmp(option,"--space-library=",16)) {
                if (!copy_program || copy_library || !option[16]) return 125;
                copy_library=option+16;
            } else if (!strcmp(option,"--space-no-libgcc")) {
                if (!copy_program || copy_no_libgcc) return 125;
                copy_no_libgcc=1;
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
