# FreeRTOS Channel I/O Contract (Stage 46.5.3)

## Scope
Define a deterministic interactive bridge over runtime ABI (`WRITE_MEM`/`READ_MEM` + `RUN/STEP`) for a FreeRTOS-style in-guest command loop.

## Memory window (guest offsets)
- `0x180` (`cmd`): command id written by operator.
- `0x184` (`arg`): optional argument.
- `0x188` (`rsp`): response code.
- `0x18C` (`task_count`): task/state introspection field.
- `0x190` (`tick_count`): guest-visible tick counter.
- `0x194` (`heap_watermark`): guest-visible heap watermark proxy.

All fields are 32-bit little-endian words.

## Command semantics
- `cmd=0`: idle/no-op.
- `cmd=1`: process command, set:
  - `rsp = 0x91`
  - `task_count = 1`
  - `tick_count += 1`
  - `heap_watermark = 0x70`
  - clear `cmd` to `0`

## Deterministic loop and timeout
- Guest continuously polls `cmd` in a loop.
- Operator sends request via `WRITE_MEM`.
- Operator advances execution via bounded `RUN`/`STEP` ticks only.
- Operator reads response via `READ_MEM`.
- Timeout semantics: if `rsp` is not observed within bounded tick budget, interaction fails.

## Acceptance gate
- `scripts/tdd/test_rv32_freertos_channel_io_e2e.sh` must pass.
