/* rv32m_image_abi.h — RV32M Image Format ABI constants
 *
 * Binary layout (little-endian):
 *   Offset  Size  Field
 *   0       4     magic = "CSRV"
 *   4       2     version (u16)
 *   6       2     flags (u16)
 *   8       4     image_bits (u32)
 *   12      4     entry_bitaddr (u32)
 *   16      4     processor_bits (u32)
 *   20      32    payload_sha256
 *   52           payload
 */
#ifndef RV32M_IMAGE_ABI_H_
#define RV32M_IMAGE_ABI_H_

#include <stdint.h>

#define RV32M_MAGIC_B0 'C'
#define RV32M_MAGIC_B1 'S'
#define RV32M_MAGIC_B2 'R'
#define RV32M_MAGIC_B3 'V'

#define RV32M_VERSION_1 1
#define RV32M_HEADER_SIZE 52

/* Offsets */
#define RV32M_OFF_MAGIC        0
#define RV32M_OFF_VERSION      4
#define RV32M_OFF_FLAGS        6
#define RV32M_OFF_IMAGE_BITS   8
#define RV32M_OFF_ENTRY        12
#define RV32M_OFF_PROC_BITS    16
#define RV32M_OFF_SHA256       20
#define RV32M_OFF_PAYLOAD      52

#endif /* RV32M_IMAGE_ABI_H_ */
