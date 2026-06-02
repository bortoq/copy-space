# RV32M Image Format v1

1. Purpose: canonical image format for loading "RISC-V-as-copy" runtime into VM space.
2. Compatibility: loader/runtime/image versions are validated before activation.

## Binary layout (v1)

All integers are little-endian.

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0      | 4    | magic | `"CSRV"` (0x43535256 LE) |
| 4      | 2    | version | Format version (1 for v1) |
| 6      | 2    | flags | Bit flags (reserved, must be 0 for v1) |
| 8      | 4    | image_bits | Size of payload in bits |
| 12     | 4    | entry_bitaddr | Entry point bit address after load |
| 16     | 4    | processor_bits | Expected processor region size in bits |
| 20     | 32   | payload_sha256 | SHA-256 digest of raw payload |
| 52     | ...  | payload | Layer image bits (byte-aligned) |

## Payload

1. Layer image bits to be copied into processor region.
2. For v1: `image_bits == processor_bits` is required.
3. Payload must be byte-aligned (`image_bits % 8 == 0`).

## Validation rules

1. `magic` must equal `"CSRV"`.
2. `version` must be in supported set (currently `[1]`).
3. `image_bits` must be byte-aligned and equal `processor_bits`.
4. `entry_bitaddr` must be in valid space range.
5. `payload_sha256` must match SHA-256 of actual payload bytes.

## Negative test vectors (mandatory)

1. Bad magic (e.g., `"BAD "`).
2. Unsupported version (e.g., `255`).
3. Declared length mismatch (`image_bits != processor_bits`).
4. SHA-256 mismatch (header digest != actual payload digest).

## Compat matrix

| Loader version | Runtime version | Image version |
|----------------|-----------------|---------------|
| v1             | v1              | v1            |

Rules:
- Image `version` must be <= Loader max supported version.
- Runtime ABI must match image `processor_bits` exactly.
- Future versions: image version can be incremented independently; loader must reject unknown versions.

## Loader ABI (in-space state machine)

The in-space loader follows a 4-phase state machine:

| Phase | Description |
|-------|-------------|
| INIT  | Prepare loader state; clear error flags; set up workspace. |
| LOAD  | Receive image bytes into space memory (via IN channel). |
| VERIFY| Validate magic/version/length/sha256 against header. |
| ACTIVATE| Set `load_src`/`load_bits`, trigger `load_req`, wait `load_done`. |

State transitions:
- INIT → LOAD: set up IN channel destination for image.
- LOAD → VERIFY: all bytes received; parse header.
- VERIFY → ACTIVATE: on success; on failure → rollback.
- ACTIVATE → DONE: after `load_done`; entry point reached.
- Any → ROLLBACK: on error (bad header, timeout, sha mismatch).

## MMIO loader mapping (v1)

See `space.h` → `vm_mmio_layout_t`:

| Register | Width | Description |
|----------|-------|-------------|
| `load_req` | 1 bit | Set to 1 to trigger load |
| `load_done` | 1 bit | Set by VM when load completes |
| `load_err` | 1 bit | Set by VM on error |
| `load_src` | ADDR_BITS | Source bit address in space |
| `load_bits` | N_BITS | Number of bits to copy (must == processor_bits) |

## Size budgets

| Limit | Value | Notes |
|-------|-------|-------|
| Max image bytes | 65536 | Hard limit for v1 |
| Max image_bits | 524288 | Limited by space size |
| Min processor_bits | 72 | At least 1 instruction |
| Max retries per phase | 3 | Before deterministic fail |
