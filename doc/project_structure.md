# Copy-Space Project Structure

This document describes the current stable construction of the project: what is active, what is legacy, and how the parts relate.

## Current State

The project is now organized around one active resident execution core:

- `src/vm/space.c` is the source of truth for resident `RV32I` execution.
- `src/vm/space.h` defines the resident state, stop reasons, trace records, and the VM object layout.
- `src/vm/rv32.c` and `src/vm/rv32.h` hold the resident execution core and trace helpers as a separate source boundary.
- `src/tools/vmrun.c` is a temporary bootstrap wrapper, not a second runtime layer.
- `scripts/tdd/*` contains the active proof gates.
- `doc/roadmap.md` contains only action stages toward the goal.
- `doc/glossary.md` defines the project terms used in the active docs.
- `doc/anticrisis_plan.md` contains the crisis-mode execution policy.
- `doc/legacy_inventory.md` freezes everything intentionally outside the active path.
- `doc/resident_orchestration_boundary.md` defines the scope of the `9.4` migration step.
- `doc/resident_orchestration_migration_plan.md` defines the execution plan for `9.4`.
- `doc/resident_orchestration_runtime_boundary.md` defines the runtime boundary for stage `15`.
- `doc/resident_startup_contract.md` defines the minimal startup contract for stage `16`.
- `doc/resident_orchestration_execution_runtime.md` defines the minimal execution runtime for stage `17`.
- `doc/resident_copy_scheduling_runtime.md` defines the minimal copy scheduling runtime for stage `18`.
- `doc/resident_test_orchestration_runtime.md` defines the minimal test orchestration runtime for stage `19`.
- `doc/resident_host_dependency_collapse_contract.md` defines the minimal host-dependency collapse contract for stage `20`.
- `doc/resident_host_independent_launch_slice.md` defines the minimal host-independent launch slice for stage `21`.
- `doc/resident_launch_control_ownership.md` defines the minimal resident launch control contract for stage `22`.
- `doc/resident_copy_scheduling_ownership.md` defines the minimal resident copy scheduling contract for stage `23`.
- `doc/resident_completion_bookkeeping_ownership.md` defines the minimal resident completion bookkeeping contract for stage `24`.
- `doc/resident_job_selection_tool_dispatch_ownership.md` defines the minimal resident job selection and tool dispatch contract for stage `25`.
- `doc/resident_control_plane_assembly_plan.md` defines the resident control plane assembly plan for stage `26`.
- `doc/resident_job_descriptor.md` defines the first resident orchestration payload contract.
- `doc/resident_job_selection.md` defines the first resident orchestration selection contract.
- `doc/resident_tool_invocation.md` defines the first resident tool invocation contract.
- `doc/resident_toolchain_control.md` defines the first resident toolchain control contract.
- `doc/host_orchestration_freeze.md` freezes host orchestration as bootstrap-only.
- `doc/resident_boundary_final.md` freezes the final resident-oriented boundary.
- `doc/resident_copicode_runtime_boundary.md` defines the runtime boundary for `10.1`.
- `doc/resident_copicode_migration_plan.md` defines the execution plan for `10.2`.
- `doc/resident_copicode_artifact.md` defines the first resident copicode artifact contract.
- `doc/resident_copicode_handoff.md` defines the handoff contract for `10.3.2`.
- `doc/resident_copicode_decision_records.md` defines the decision record contract for `10.3.3`.
- `doc/resident_copicode_toolchain_control_records.md` defines the toolchain control record contract for `10.3.4`.
- `doc/resident_copicode_launch_completion.md` defines the launch-completion contract for `10.3.5`.
- `doc/riscv_migration_plan.md` defines the staged migration from resident `RISC-V` compute backend to host-dependency collapse.
- `doc/resident_riscv_boundary_freeze.md` defines the frozen `space.*` boundary for the next `RISC-V` migration.
- `doc/resident_riscv_extraction_boundary.md` defines the isolated source boundary for resident `RISC-V`.
- `doc/resident_riscv_compute_backend.md` defines the resident compute backend usage boundary for `RISC-V`.
- `doc/resident_riscv_proof_tools_preparation.md` defines the proof-tools preparation boundary for `RISC-V`.

`C3_RUN` exists only as a legacy artifact. It is not part of the active proof path.

## Layer Roles

### 1. Resident Core

`src/vm/space.c`:

- Implements the address-space emulator shell and channel/MMIO dispatcher.
- Calls into `src/vm/rv32.c` for resident `RV32I` execution.
- Keeps host-visible state transitions stable.

`src/vm/space.h`:

- Defines the VM object.
- Defines guest-state addresses and stop reasons.
- Defines trace record and trace info layouts.
- Defines the MMIO/channel layout.

`src/vm/rv32.c`:

- Implements resident `RV32I` execution.
- Owns guest load, step, stop, trace emission, and control-plane behavior.
- Owns the resident `trace/state` proof path.
- Owns the resident `request/response` control plane.

### 2. Host Wrapper

`src/tools/vmrun.c`:

- Loads an image into `vm->space`.
- Runs the VM for a bounded number of ticks.
- Optionally dumps the final space image.

It does not implement guest semantics.
It does not interpret `RISC-V`.
It is a thin temporary bootstrap shell around `space.c`.
It does not own target-architecture semantics.

### 3. Resident Proof Gates

`src/tools/rv32_space_fault_proof.c`:

- Proves resident alignment and bounds fault behavior.

`src/tools/rv32_space_trace_proof.c`:

- Proves resident trace emission.
- Proves trace extraction through the resident ABI.
- Proves trace/state consistency.

`src/tools/rv32_space_control_proof.c`:

- Proves the resident request/response control plane.
- Verifies the minimal handshake and roundtrip behavior.

`src/tools/c3_addi_proof.c`:

- Legacy artifact.
- Kept for archival/reference purposes only.
- Not part of the active proof path.

### 4. Active Test Orchestration

`scripts/tdd/run_rv32_space_closure.sh`:

- Runs the resident closure gates only.

`scripts/tdd/run_all.sh`:

- Runs the active baseline and host-contract gates.
- Serves as the current minimal verification entrypoint.

### 5. Documentation

`doc/roadmap.md`:

- Contains only staged actions toward the project goal.
- No audit content.
- No diagnostic content.

`doc/glossary.md`:

- Defines the project terms used in the active docs.
- Adds a term whenever the active docs need a word that is not already defined.

`doc/anticrisis_plan.md`:

- Defines the crisis-mode operating policy.
- Defines the single active path and kill criteria.

`doc/space_minimal_host_contract.md`:

- Defines the minimal host wrapper contract.
- Draws the boundary between temporary bootstrap responsibilities and resident semantics.

`doc/legacy_inventory.md`:

- Lists frozen legacy material.
- States the rule for what is and is not active.

`doc/resident_orchestration_boundary.md`:

- Defines what belongs to resident orchestration.
- Defines what is intentionally out of scope.

`doc/resident_orchestration_migration_plan.md`:

- Defines the execution steps for stage `9.4`.
- Keeps host bootstrap, resident orchestration, and toolchain migration separated.

`doc/resident_orchestration_runtime_boundary.md`:

- Defines the runtime boundary for stage `15`.
- Describes resident orchestration entrypoints, state model, interfaces, and verification hooks.

`doc/resident_startup_contract.md`:

- Defines the minimal startup contract for stage `16`.
- Describes fixed slots, bootstrap payload, and first handoff responsibilities.

`doc/resident_orchestration_execution_runtime.md`:

- Defines the minimal resident orchestration execution runtime for stage `17`.
- Describes the execution entrypoint, state model, interfaces, and verification hooks.

`doc/resident_copy_scheduling_runtime.md`:

- Defines the minimal resident copy scheduling runtime for stage `18`.
- Describes the scheduling shape, state model, interfaces, and verification hooks.

`doc/resident_test_orchestration_runtime.md`:

- Defines the minimal resident test orchestration runtime for stage `19`.
- Describes the job-selection shape, state model, interfaces, and verification hooks.

`doc/resident_host_dependency_collapse_contract.md`:

- Defines the minimal host-dependency collapse contract for stage `20`.
- Describes the boundary conditions required before actual host-dependency collapse.

`doc/resident_host_independent_launch_slice.md`:

- Defines the minimal host-independent launch slice for stage `21`.
- Describes the first tiny path where resident runtime owns launch/completion and host stays bootstrap-only.

`doc/resident_launch_control_ownership.md`:

- Defines the minimal resident launch control contract for stage `22`.
- Describes the launch decision ownership boundary after bootstrap.

`doc/resident_copy_scheduling_ownership.md`:

- Defines the minimal resident copy scheduling contract for stage `23`.
- Describes the copy decision ownership boundary after bootstrap.

`doc/resident_completion_bookkeeping_ownership.md`:

- Defines the minimal resident completion bookkeeping contract for stage `24`.
- Describes the completion record ownership boundary after bootstrap.

`doc/resident_job_selection_tool_dispatch_ownership.md`:

- Defines the minimal resident job selection and tool dispatch contract for stage `25`.
- Describes the job and tool ownership boundary after bootstrap.

`doc/resident_control_plane_assembly_plan.md`:

- Defines the resident control plane assembly plan for stage `26`.
- Describes the minimal resident-owned control loop before host-dependency collapse.

`doc/resident_job_descriptor.md`:

- Defines the first resident orchestration payload.
- Serves as the contract for stage `9.4.5`.

`doc/resident_job_selection.md`:

- Defines the first resident orchestration selection rule.
- Serves as the contract for stage `9.4.6`.

`doc/resident_tool_invocation.md`:

- Defines the first resident tool invocation record.
- Serves as the contract for stage `9.4.7`.

`doc/resident_toolchain_control.md`:

- Defines the first resident toolchain control record.
- Serves as the contract for stage `9.4.9`.

`doc/host_orchestration_freeze.md`:

- Freezes host orchestration as bootstrap-only.
- States what is no longer active.

`doc/resident_boundary_final.md`:

- Freezes the final resident-oriented boundary.
- States what belongs in `space.*`, host, and resident boundaries.

`doc/resident_copicode_runtime_boundary.md`:

- Defines the runtime boundary for stage `10.1`.
- Describes resident runtime entrypoints, state, interfaces, and verification hooks.

`doc/resident_copicode_migration_plan.md`:

- Defines the execution plan for stage `10.2`.
- Describes how orchestration and toolchain control will move into resident copicode.

`doc/resident_copicode_artifact.md`:

- Defines the first resident copicode artifact format.
- Serves as the contract for stage `10.3.1`.

`doc/resident_copicode_handoff.md`:

- Defines the resident copicode handoff record.
- Serves as the contract for stage `10.3.2`.

`doc/resident_copicode_decision_records.md`:

- Defines the resident copicode decision record.
- Serves as the contract for stage `10.3.3`.

`doc/resident_copicode_toolchain_control_records.md`:

- Defines the resident copicode toolchain control record.
- Serves as the contract for stage `10.3.4`.

`doc/resident_copicode_launch_completion.md`:

- Defines the resident copicode launch-completion record.
- Serves as the contract for stage `10.3.5`.

`doc/riscv_migration_plan.md`:

- Defines the staged migration path for resident `RISC-V`.
- Covers boundary freeze, extraction, resident compute backend usage, orchestration migration, and host-dependency collapse.

`doc/resident_riscv_boundary_freeze.md`:

- Freezes `space.*` as the address-space emulator boundary.
- Serves as the contract for stage `11`.

`doc/resident_riscv_extraction_boundary.md`:

- Freezes the extraction boundary for resident `RISC-V`.
- Serves as the contract for stage `12`.

`doc/resident_riscv_compute_backend.md`:

- Defines the resident compute backend usage boundary.
- Serves as the contract for stage `14`.

`doc/resident_riscv_proof_tools_preparation.md`:

- Defines the proof-tools preparation boundary.
- Serves as the contract for stage `13`.

## Diagram

```mermaid
flowchart TD
  A[docs/roadmap.md] --> B[active resident plan]
  C[docs/anticrisis_plan.md] --> B
  D[src/vm/space.h] --> E[src/vm/space.c]
  E --> F[src/vm/rv32.c]
  F --> G[resident proof gates]
  G --> H[scripts/tdd/run_rv32_space_closure.sh]
  H --> I[scripts/tdd/run_all.sh]
  J[src/tools/vmrun.c] --> K[minimal host wrapper]
  K --> I
  F --> L[resident control plane]
  F --> M[resident trace/state proof]
  F --> N[resident fault semantics]
  O[src/tools/c3_addi_proof.c] -. legacy only .-> P[archive/reference]
```

## What Is Active

- Resident execution in `space.c`
- Resident trace/state proof
- Resident fault semantics
- Resident request/response control plane
- Minimal host wrapper
- Active proof gates in `scripts/tdd`

## What Is Legacy

- `C3_RUN` as a runtime path
- `c3_addi_proof` as an active proof mechanism
- Any scaffold-only or synthetic-trace-based path
- Any host-side guest semantics beyond the minimal wrapper contract
