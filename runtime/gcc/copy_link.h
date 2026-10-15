#ifndef CS_GCC_COPY_LINK_H
#define CS_GCC_COPY_LINK_H
#include <stddef.h>
#include <stdint.h>
struct cs_copy_link_error { size_t line; const char *message; };
/* Prototype: one function, with a test caller reporting r0. */
int cs_copy_link_leaf(unsigned char *, size_t, unsigned, const char *, size_t,
                       const char *, const uint32_t *, unsigned,
                       struct cs_copy_link_error *);
/* Multiple functions, direct calls and stack frames. */
int cs_copy_link_program(unsigned char *, size_t, unsigned, const char *, size_t,
                       const char *, const uint32_t *, unsigned,
                       struct cs_copy_link_error *);
/* Explicit data/stack memory size; power of two >= 8192, at image end. */
int cs_copy_link_program_memory(unsigned char *, size_t, unsigned, uint32_t,
                        const char *, size_t, const char *, const uint32_t *, unsigned,
                        struct cs_copy_link_error *);
struct cs_copy_object { const char *assembly; size_t size; };
/* Scoped locals and strong/common/weak resolution. Scratch holds text + NUL;
   it must not overlap the inputs or image. One input uses program linking. */
int cs_copy_link_objects(unsigned char *, size_t, unsigned,
                        const struct cs_copy_object *, unsigned,
                        char *, size_t,
                        const char *, const uint32_t *, unsigned,
                        struct cs_copy_link_error *);
int cs_copy_link_objects_memory(unsigned char *, size_t, unsigned, uint32_t,
                        const struct cs_copy_object *, unsigned,
                        char *, size_t, const char *, const uint32_t *, unsigned,
                        struct cs_copy_link_error *);
/* Same linking, with an internally allocated exact-size rewrite buffer. */
int cs_copy_link_objects_alloc(unsigned char *, size_t, unsigned, uint32_t,
                        const struct cs_copy_object *, unsigned,
                        const char *, const uint32_t *, unsigned,
                        struct cs_copy_link_error *);
/* A regular ar archive of copy assembly (up to 64 members). Extract members
   for unresolved strong references, iterating dependencies to closure.
   Selected inputs, including explicit objects, must fit the eight-unit limit.
   Weak imports and definitions already supplied by inputs do not extract. */
int cs_copy_link_archive_alloc(unsigned char *, size_t, unsigned, uint32_t,
                        const struct cs_copy_object *, unsigned,
                        const char *, size_t,
                        const char *, const uint32_t *, unsigned,
                        struct cs_copy_link_error *);
#endif
