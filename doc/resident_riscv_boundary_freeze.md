# Resident RISC-V Boundary Freeze

This document freezes the `space.*` boundary before the next `RISC-V` migration step.

## Purpose

The purpose of this freeze is to keep `space.*` as the address-space emulator only, while `RISC-V` implementation work moves into isolated resident boundaries.

## Allowed Changes in `space.*`

Only the following classes of changes are allowed in `space.*`:

- performance improvements,
- portability improvements,
- reliability improvements,
- diagnostics improvements,
- maintainability improvements,
- testability improvements.

## Forbidden Changes in `space.*`

`space.*` must not gain:

- new `RISC-V` semantics,
- orchestration logic,
- proof logic,
- alternative emulator logic,
- toolchain logic,
- compiler/runtime helpers,
- test harness internals.

## Host and Resident Interface

The host/resident handoff is limited to:

- loading a boot image,
- starting the first resident entrypoint,
- bounding execution by the requested tick count,
- dumping state and diagnostics,
- copying semi-intervals and channel data through the emulator contract.

All `RISC-V` execution state must live outside host-side `space.*` functionality.

## Verification Boundary

The freeze is valid only if:

- `space_contract.md` remains aligned with this freeze,
- the active documentation map names this freeze,
- the migration plan treats `space.*` as a stable boundary.
