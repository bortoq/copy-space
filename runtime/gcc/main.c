/* This adapter is executed by RV32I copies inside Space. */
#include "copy_space.h"
#include "job.h"
#ifdef CS_GCC_FRAMED_OUTPUT
#include "response.h"
#include "files.h"
#endif
#include <stdio.h>
#include <string.h>
extern int __real_main(int argc, char **argv);
static struct cs_gcc_job job;
static unsigned char *packet;
#ifdef CS_GCC_FRAMED_OUTPUT
static const char *output_file;
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
