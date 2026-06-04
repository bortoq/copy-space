# Resident Orchestration Migration Plan

This plan covers stage `9.4`: migrate orchestration and toolchain control into resident copicode while keeping `space.*` free of non-emulator residue.

## Goals

- Move orchestration decisions into resident code after bootstrap.
- Keep the host only as a loader and bootstrap shim until the resident path can take over.
- Avoid adding any orchestration semantics to `space.*`.
- Make every step machine-checkable and reversible by git.

## Phase 1. Define the resident orchestration contract

- Define which job metadata must be passed to resident code.
- Define which lifecycle states belong to resident orchestration.
- Define which results must be observable back on the host boundary.
- Define the minimal bootstrap handoff from host to resident code.

## Phase 2. Encode resident job descriptors

- Add a resident job descriptor format.
- Add a resident job queue or equivalent scheduling input.
- Add validation for descriptor shape and bounds.
- Add a gate that proves resident code can consume one descriptor.

## Phase 3. Move orchestration decisions into resident code

- Move job selection into resident code.
- Move job launch sequencing into resident code.
- Move completion bookkeeping into resident code.
- Preserve host bootstrap only as the initial entrypoint.

## Phase 4. Move tool invocation into resident code

- Convert the tool invocation path to resident-controlled calls.
- Keep host-side tool invocation only where it is bootstrap-only.
- Add proof gates for one resident tool launch and one resident completion.

## Phase 5. Remove host orchestration from the active path

- Remove host-side orchestration code that is no longer needed after resident takeover.
- Keep only the minimal bootstrap shim on the host.
- Verify that host code no longer makes active scheduling decisions.

## Phase 6. Migrate toolchain control progressively

- Move preparation of resident workloads into resident code where possible.
- Keep build-time generation separate from runtime orchestration.
- Remove any host helper that is provably bootstrap-only and no longer active.

## Phase 7. Freeze the final boundary

- Document the final resident orchestration boundary.
- Document what remains host-only and why.
- Ensure `space.*` still contains only the emulator contract.

## Risk Controls

- One change per phase.
- One proof gate per phase.
- No change to `space.*` semantics.
- No synthetic proof source.
- No orchestration logic inside `space.*`.
