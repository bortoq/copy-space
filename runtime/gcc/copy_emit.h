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
struct cs_copy_program {
    struct cs_copy_image image;
    uint32_t code_begin, code_end, code_limit;
};
enum cs_copy_bit_operation { CS_COPY_AND, CS_COPY_OR, CS_COPY_XOR };
int cs_copy_image_init(struct cs_copy_image *, unsigned char *, size_t,
                       unsigned, uint32_t);
int cs_copy_constant(struct cs_copy_image *, uint32_t, unsigned, uint32_t);
int cs_copy_row(struct cs_copy_image *, unsigned, uint32_t, uint32_t, uint32_t);
int cs_copy_emit(struct cs_copy_image *, uint32_t, uint32_t, uint32_t);
int cs_copy_add32(struct cs_copy_image *, uint32_t, uint32_t, uint32_t,
                  uint32_t, uint32_t, uint32_t);
int cs_copy_sub32(struct cs_copy_image *, uint32_t, uint32_t, uint32_t,
                  uint32_t, uint32_t, uint32_t);
int cs_copy_bits32(struct cs_copy_image *, enum cs_copy_bit_operation,
                   uint32_t, uint32_t, uint32_t, uint32_t);
int cs_copy_program_init(struct cs_copy_program *, unsigned char *, size_t,
                        unsigned, uint32_t, uint32_t);
int cs_copy_program_next(struct cs_copy_program *);
int cs_copy_program_patch_jump(struct cs_copy_program *, uint32_t, uint32_t);
int cs_copy_program_emit(struct cs_copy_program *, uint32_t, uint32_t, uint32_t);
int cs_copy_program_add32(struct cs_copy_program *, uint32_t, uint32_t, uint32_t,
                          uint32_t, uint32_t, uint32_t);
int cs_copy_program_sub32(struct cs_copy_program *, uint32_t, uint32_t, uint32_t,
                          uint32_t, uint32_t, uint32_t);
int cs_copy_program_bits32(struct cs_copy_program *, enum cs_copy_bit_operation,
                           uint32_t, uint32_t, uint32_t, uint32_t);
int cs_copy_program_finish(struct cs_copy_program *, uint32_t);
#ifdef __cplusplus
}
#endif
#endif
