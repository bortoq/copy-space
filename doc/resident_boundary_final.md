# Resident Boundary Final

This document freezes the final resident-oriented boundary reached by the orchestration migration work.

## What Lives in `space.*`

`space.*` is only the address-space emulator.

It may provide:

- bit-space semi-interval copying,
- stdin/stdout copy-in and copy-out channels,
- loading of a single boot instruction before the first tick,
- bounded execution by the requested tick count,
- minimal host interaction needed to support the emulator contract.

It must not contain:

- proof logic,
- resident orchestration logic,
- `forth0` logic,
- toolchain control logic,
- alternative emulator logic,
- scheduler or launch logic,
- test harness internals,
- residual runtime from any removed subsystem.

## What Lives on the Host

The host is bootstrap-only.

It may:

- load images,
- launch the first resident entrypoint,
- bound execution,
- dump state,
- emit diagnostics.

It must not:

- select resident jobs after bootstrap,
- invoke resident tools as an active execution layer,
- schedule resident work,
- own resident lifecycle state after bootstrap.

## What Lives in Resident Boundaries

The resident migration now has separate boundaries for:

- orchestration contract,
- job descriptors,
- job selection,
- tool invocation,
- toolchain control.

These boundaries are data-contract checkpoints first, and execution migration steps later.

## Freeze Rule

Any future change that adds non-emulator behavior to `space.*` is a new project decision, not a refactor.

Any future change that expands host orchestration beyond bootstrap-only is outside this boundary.
