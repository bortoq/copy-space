# Resident RISC-V Extraction Boundary

This document freezes the extraction boundary used by stage `12`.

## Purpose

The purpose of this boundary is to keep resident `RISC-V` execution in an isolated source boundary and keep `space.*` as the address-space emulator only.

## Extracted Resident Core

The resident `RISC-V` implementation lives in:

- `src/vm/rv32.c`
- `src/vm/rv32.h`

This boundary owns:

- resident state ownership,
- resident instruction execution ownership,
- resident trace/state ownership,
- resident control-plane behavior.

## Host Wrapper Relationship

`src/tools/vmrun.c` remains a host wrapper only.

It may:

- load an image,
- run bounded ticks,
- dump state,
- emit diagnostics.

It may not:

- implement guest semantics,
- interpret `RISC-V`,
- own resident state,
- own trace/state proof logic,
- own resident control-plane behavior.

## Verification Rule

The extraction is considered valid only if:

- the resident core is in separate source files,
- the source tree map names the boundary explicitly,
- the roadmap marks stage `12` as source-boundary extraction rather than ISA expansion.
