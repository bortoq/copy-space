# RV32M Channel ABI v1

## Scope

1. Control-plane mailbox protocol over VM MMIO for `load/run/step/stop/io` orchestration.
2. This is a minimal ABI layer and replaces reliance on TERM0-only flows.

## MMIO mailbox fields

1. `ch_req/ch_done/ch_err`
2. `ch_op` (8-bit opcode)
3. `ch_a/ch_b/ch_c` (arguments)

## Opcodes (v1)

1. `0` = `NOP/ACK`
2. `1` = `STOP` (sets `MMIO.HALT=1`)
3. `2` = `STEP_BUDGET` (`ch_c` -> watchdog limit, enables watchdog)
4. `3` = `LOAD_IMAGE` (LOAD handler phase). Parameters: `ch_a` = source address in space (bits), `ch_b` = number of bits to copy. Copies `ch_b` bits from `space[ch_a]` to processor area (bit 0). Validates `ch_b == processor_bits` and source is in workspace area. Sets `ch_err` on validation failure. *Status: implemented.*
5. `4` = `LOAD_ACK` (ACTIVATE handler phase). No parameters. Acknowledges load completion, resets watchdog state, sets `ch_done`. *Status: implemented.*
6. `5` = `IO_WRITE` (IO output handler). Parameters: `ch_a` = source address in space (bits), `ch_b` = length in bytes. Reads `ch_b` bytes from `space[ch_a/8]` and writes to stdout. Validates byte alignment and bounds. *Status: implemented.*
7. `6` = `STATUS` (Diagnostic handler). Output-only — writes current tick counter to `space[ch_a]` (ADDR_BITS), halt state (0/1) to `space[ch_b]` bit 0, last error kind to `space[ch_c]` (N_BITS). *Status: implemented.*

## Error model

1. Unknown opcode -> `ch_err=1`, `ch_done=1`.
2. All operations clear `ch_req` on completion.

## ABI Version Register

1. `ch_abi_version` — 8-bit read-only register, located at MMIO offset immediately after `ch_c`.
2. Always reads as `1` for v1 of the channel ABI.
3. Host software MUST read this register before negotiating any opcode-dependent protocol to verify compatibility.

## Status

The following items document implementation status across the channel ABI surface:

| # | Item | Status |
|---|------|--------|
| 1.1 | NOP/ACK opcode | implemented |
| 1.2 | STOP opcode | implemented |
| 1.3 | STEP_BUDGET opcode | implemented |
| 1.4 | LOAD_IMAGE opcode | implemented |
| 1.5 | LOAD_ACK opcode | implemented |
| 1.6 | IO_WRITE opcode | implemented |
| 1.7 | STATUS opcode | implemented |
| 1.8 | ch_err on unknown opcode | implemented |
| 1.9 | ch_req cleared on completion | implemented |
| 2.1 | ABI version register (ch_abi_version) | implemented |
| 2.2 | Compat shim for future versions | planned |
| 2.3 | Version negotiation contract tests | planned |
| 2.4 | Backward-compat guarantee for v1 opcodes | planned |

## Compatibility

1. ABI version is encoded in the `ch_abi_version` register and validated by contract tests.
2. Future versions must preserve v1 opcodes or provide explicit compat shim.

| ABI Version | Opcodes | Status |
|-------------|---------|--------|
| 1           | 0–6     | Current |
