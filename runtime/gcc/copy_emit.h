#ifndef CS_GCC_COPY_EMIT_H
#define CS_GCC_COPY_EMIT_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
struct cs_copy_image {
    unsigned char *data;
    size_t bytes;
    uint32_t space_bits, layer, layer_bits;
    unsigned address_bits, count_bits, instruction_bits, slot;
};
int cs_copy_image_init(struct cs_copy_image *, unsigned char *, size_t,
                       unsigned, uint32_t);
int cs_copy_constant(struct cs_copy_image *, uint32_t, unsigned, uint32_t);
int cs_copy_row(struct cs_copy_image *, unsigned, uint32_t, uint32_t, uint32_t);
int cs_copy_emit(struct cs_copy_image *, uint32_t, uint32_t, uint32_t);
int cs_copy_add32(struct cs_copy_image *, uint32_t, uint32_t, uint32_t,
                  uint32_t, uint32_t, uint32_t);
#ifdef __cplusplus
}
#endif
#endif
