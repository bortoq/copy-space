# RV32 Guest Handoff Envelope (Stage-22)

Status: frozen

## Envelope fields
- `base_bits`: guest memory destination offset from `G_MEM_BASE` in bits.
- `size_bits`: payload transfer size in bits.
- `entry_bits`: guest entry offset from `G_MEM_BASE` in bits.
- `flags`: loader/runtime flags bitset.
- `checks`: mandatory validation checks executed before state transition to `loaded`.

## ABI mapping
- Channel op `LOAD_CODE` (`op=7`):
  - `ch_a`: source bit address in workspace.
  - `ch_b`: `base_bits`.
  - `ch_c`: `size_bits`.
- `entry_bits` and `flags` are currently constrained for stage-22 baseline:
  - `entry_bits=0` (entry at guest base),
  - `flags=0` (no optional behaviors enabled).

## Mandatory checks
- Bounds check: source and destination windows must fit in VM space.
- Alignment check: bit ranges must be byte-addressable where required by transfer path.
- Protocol/state check: `RUN`/`STEP` are forbidden before successful `LOAD_CODE`.
- Determinism check: repeated `LOAD_CODE + RUN/STEP + READ_*` with same inputs must produce identical observable outputs.

## State model
- `idle` -> `loaded` only on successful `LOAD_CODE`.
- `loaded` -> `running` on `RUN`/`STEP`.
- `running` -> `stopped` on halt/watchdog/stop condition.
- Invalid transitions fail fast with ABI protocol error code.
