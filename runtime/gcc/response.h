#ifndef CS_GCC_RESPONSE_H
#define CS_GCC_RESPONSE_H
#include <stddef.h>
int cs_gcc_capture_write(int fd, const void *data, size_t size);
int cs_gcc_response(int status, const char *output_file,
                    int (*write_bytes)(const void *, unsigned));
void cs_gcc_capture_reset(void);
#endif
