#ifndef COPY_SPACE_C_H_
#define COPY_SPACE_C_H_

#include <stddef.h>

/* stdin/stdout only; return byte count, 0 at EOF, or a negative error. */
int cs_read(void *buffer, unsigned int bytes);
int cs_write(const void *buffer, unsigned int bytes);
void cs_exit(int code) __attribute__((noreturn));

void *memcpy(void *dst, const void *src, size_t bytes);
void *memmove(void *dst, const void *src, size_t bytes);
void *memset(void *dst, int value, size_t bytes);
int memcmp(const void *a, const void *b, size_t bytes);

#endif
