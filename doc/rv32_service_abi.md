# RV32 Service ABI v1

This document defines the production channel service ABI for running RV32 code in copy-space.

## 1. Tick-based execution model

The VM has no wall-clock time. All execution limits are expressed in ticks.
- `max_ticks`: hard tick limit per operation.
- `watchdog_ticks`: tick limit without forward progress.
- On limit hit, service returns `STOP_BUDGET_EXCEEDED`.

## 2. Operations

- `LOAD_IMAGE`: load RV runtime image.
- `LOAD_CODE`: load guest code/data segments.
- `RUN`: run until stop/trap/budget.
- `STEP`: execute bounded ticks.
- `STOP`: cooperative stop.
- `STATUS`: query stop state and counters.
- `READ_MEM` / `WRITE_MEM`.
- `READ_REGS`.

## 3. Image/program constraints

- little-endian RV32 payload.
- segment bounds must fit VM limits.
- alignment and permissions checks are mandatory.
- checksum/sha validation is mandatory for image-level loads.

## 4. Error model

- `ERR_DECODE`
- `ERR_MEM_ALIGN`
- `ERR_MEM_BOUNDS`
- `ERR_BUDGET` (tick budget exceeded)
- `ERR_UNSUPPORTED_ISA`
- `ERR_PROTOCOL`

## 5. Compatibility

ABI policy is N/N-1 for channel message schema.
