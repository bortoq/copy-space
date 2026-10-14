#ifndef CS_GCC_JOB_H
#define CS_GCC_JOB_H
#include <stddef.h>
#define CS_GCC_JOB_MAX (16u*1024u*1024u)
struct cs_gcc_job { int argc; char **argv; };
/* Initialize job to {0,NULL}. Caller retains packet while files are mounted. */
int cs_gcc_job_decode(unsigned char *packet, size_t size, struct cs_gcc_job *job);
/* Read exactly one packet; successful storage remains owned by caller. */
int cs_gcc_job_read(int (*read_bytes)(void *, unsigned), unsigned char **storage,
                    struct cs_gcc_job *job);
void cs_gcc_job_release(struct cs_gcc_job *job);
#endif
