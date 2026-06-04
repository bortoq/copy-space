# RISC-V Migration Plan

Goal: migrate all remaining host-side `RISC-V`-related functionality into resident copicode with minimal risk, while keeping `space.*` stable as the address-space emulator contract.

## Phase 1. Freeze the boundary

- Freeze `src/vm/space.*` against functional changes.
- Preserve only performance, portability, reliability, diagnostics, and maintainability fixes there.
- Keep `space.c` as the address-space emulator and nothing more.

## Phase 2. Extract resident RISC-V implementation into isolated source

- Move `RISC-V` resident execution logic into dedicated source files and keep clear interfaces to `space.*`.
- Keep host wrapper and resident execution responsibilities separate.
- Ensure the extraction is mechanically verifiable by the current gates.

## Phase 3. Rehost the proof tools into resident form

- Convert the current `rv32_space_*` proof tools into resident workloads or resident-controlled tests.
- Preserve one machine-checkable gate per proof slice.
- Remove any remaining dependence on synthetic traces or host-authored state.

## Phase 4. Convert orchestration into copicode

- Move `vmrun`-style orchestration into resident copicode.
- Move test orchestration into resident copicode.
- Keep a tiny bootstrap host wrapper only for loading and kicking the first resident instruction.
- Use `doc/resident_orchestration_boundary.md` as the scope boundary for this phase.
- Use `doc/resident_orchestration_migration_plan.md` as the execution plan for this phase.

## Phase 5. Convert `forth0` and the compiler path

- Turn the compiler/runtime path into resident workloads.
- Preserve bootstrap-only host code only as a temporary loader.
- Migrate the compiler output and execution loop into address-space-managed code.

## Phase 6. Convert `RISC-V` toolchain components

- Migrate any remaining `RISC-V`-specific host helpers into resident code.
- Keep host helpers only when they are provably bootstrap-only.
- Remove legacy host semantics once the resident path is verified.

## Phase 7. Collapse the host layer

- Reduce the host wrapper to minimal boot and dump responsibilities.
- Remove host-side semantics that have already been proven resident.
- Preserve the `space.*` contract as a stable emulator boundary.

## Risk Controls

- One real-proof gate per step.
- No synthetic traces as source of truth.
- No bootstrap-only path counted as closure.
- No functional changes to `space.*` unless explicitly approved as a new project decision.
