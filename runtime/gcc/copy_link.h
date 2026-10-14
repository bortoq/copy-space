#ifndef CS_GCC_COPY_LINK_H
#define CS_GCC_COPY_LINK_H
#include <stddef.h>
#include <stdint.h>
struct cs_copy_link_error { size_t line; const char *message; };
/* Prototype: one register-only leaf, with a test caller reporting r0. */
int cs_copy_link_leaf(unsigned char *, size_t, unsigned, const char *, size_t,
                       const char *, const uint32_t *, unsigned,
                       struct cs_copy_link_error *);
#endif
