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

## Error model

1. Unknown opcode -> `ch_err=1`, `ch_done=1`.
2. All operations clear `ch_req` on completion.

## Compatibility

1. ABI version is encoded by documentation and validated by contract tests.
2. Future versions must preserve v1 opcodes or provide explicit compat shim.
