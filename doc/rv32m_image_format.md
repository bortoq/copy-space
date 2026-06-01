# RV32M Image Format v1

1. Purpose: canonical image format for loading "RISC-V-as-copy" runtime into VM space.
2. Compatibility: loader/runtime/image versions are validated before activation.

## Header (fixed)

1. `magic[4]` = `CSRV`
2. `version_u16` = 1
3. `flags_u16`
4. `image_bits_u32`
5. `entry_bitaddr_u32`
6. `processor_bits_u32`
7. `payload_sha256[32]`

## Payload

1. Layer image bits to be copied into processor region.
2. For v1: `image_bits == processor_bits` is required.

## Validation rules

1. `magic` must match.
2. `version` must be supported.
3. `image_bits` must be byte-aligned and equal to runtime contract for v1.
4. `entry_bitaddr` must be in workspace region.
5. `payload_sha256` must match both pre-send and post-write readback.

## Negative vectors (mandatory)

1. Bad magic.
2. Unsupported version.
3. Declared length mismatch.
4. SHA mismatch.

## MMIO loader mapping (v1)

1. `load_src` -> payload source address in space.
2. `load_bits` -> number of bits to copy.
3. `load_req/load_done/load_err` -> handshake.
