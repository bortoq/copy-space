# Resident Copicode Runtime Boundary

This document defines the boundary for stage `10.1`.

## Scope

Resident copicode runtime means the resident execution layer that will eventually own:

- orchestration entrypoints,
- job lifecycle state,
- job selection interfaces,
- tool invocation interfaces,
- toolchain control interfaces,
- runtime verification hooks.

## Target State

The target state is a resident runtime boundary that can host the orchestration and toolchain control behavior without adding non-emulator logic to `space.*`.

## Not In Scope

This boundary does not include:

- `space.*` semantics changes,
- new guest ISA support,
- host orchestration expansion,
- proof logic inside the emulator,
- `C3_RUN` recovery,
- unrelated service tracks.

## Rules

- Runtime entrypoints must be resident-owned.
- Runtime state must be resident-owned.
- Runtime interfaces must be explicit and machine-checkable.
- Verification gates must validate the boundary before execution migration.
- `space.*` remains only the address-space emulator.

## Relation to Existing Documents

- `doc/resident_orchestration_boundary.md` defines the orchestration scope.
- `doc/resident_boundary_final.md` freezes the host/resident division.
- This document defines the runtime layer that sits behind those boundaries.
