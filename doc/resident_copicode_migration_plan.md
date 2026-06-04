# Resident Copicode Migration Plan

This document defines the executable plan for stage `10.2`.

## Goal

Move orchestration and toolchain control into resident copicode without adding non-emulator logic to `space.*`.

## Phase 1. Define the resident copicode artifact boundary

- Define the resident copicode artifact type.
- Define how resident workload code is represented at runtime.
- Define how the artifact is loaded without changing `space.*` behavior.

## Phase 2. Define the resident copicode execution boundary

- Define the resident execution entrypoint for the artifact.
- Define how job selection feeds the entrypoint.
- Define how tool invocation feeds the entrypoint.
- Define how toolchain control feeds the entrypoint.

## Phase 3. Define the migration shims

- Keep host bootstrap only for loading the first resident artifact.
- Keep host dump and diagnostics only as observability helpers.
- Remove host-side orchestration from the active path once resident entrypoint takeover is proven.

## Phase 4. Define verification gates

- Add one gate for artifact loading.
- Add one gate for resident entrypoint handoff.
- Add one gate for toolchain control takeover.
- Add one gate for host-side orchestration removal.

## Phase 5. Freeze the final state

- Freeze the new resident copicode boundary.
- Freeze the host responsibilities that remain bootstrap-only.
- Update the structure documentation to reflect the migrated boundary.

## Rule

This plan does not add orchestration logic to `space.*`.
