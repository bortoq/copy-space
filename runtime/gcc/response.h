#ifndef CS_GCC_RESPONSE_H
#define CS_GCC_RESPONSE_H
#include <stddef.h>
#include <stdint.h>
struct cs_gcc_result {
    uint32_t status;
    const unsigned char *out, *err, *file;
    uint32_t out_size,err_size,file_size;
};
int cs_gcc_response_decode(const void *packet, size_t size, struct cs_gcc_result *result);
int cs_gcc_capture_write(int fd, const void *data, size_t size);
int cs_gcc_response(int status, const char *output_file,
                    int (*write_bytes)(const void *, unsigned));
void cs_gcc_capture_reset(void);
#endif
