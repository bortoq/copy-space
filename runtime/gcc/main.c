/* This adapter is executed by RV32I copies inside Space. */
#include "copy_space.h"
#include "job.h"
#include <stdio.h>
extern int __real_main(int argc, char **argv);
static struct cs_gcc_job job;
static unsigned char *packet;

int __wrap_main(void)
{
    if (cs_gcc_job_read(cs_read,&packet,&job)) {
        fputs("gcc: invalid input job\n",stderr);
        return 125;
    }
    return __real_main(job.argc,job.argv);
}
