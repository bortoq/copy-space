# Contract: Final Migration of RISC-V Emulator Into Space

Status: Draft for execution  
Date: 2026-06-01

## 1. Goal

Complete the final migration of RISC-V execution into space so that RISC-V code runs through an in-space RISC-V emulator service, with no host-side translation/emulation assistance during runtime.

Runtime VM is explicitly allowed and remains unchanged as the execution substrate.

## 2. Completion Contract (Hard Gate)

The stage **"final migration of RISC-V emulator into space"** is complete only if the following contract is satisfied:

1. Running an RV32 binary test (example: SHA-256 test image) requires exactly:
   - Runtime VM binary (binary #1)
   - RISC-V emulator-in-space binary/image (binary #2)
   - Test guest binary (binary #3)
2. No Python/shell/Forth0 helper is in the runtime execution path of the test.
3. No host-side RV decode/trace/step/emulation is used in the runtime execution path.
4. Test orchestration may launch binaries, but may not transform or emulate guest logic.
5. Result correctness must be obtained through channel ABI interaction with the in-space emulator (register/memory/state reads), not through host emulation comparison.

If any of the above is false, this stage is not complete.

## 3. Scope Boundaries

In scope:
- In-space RV32 emulator service and its channel protocol.
- Loading guest binary into emulator-owned memory via channel operations.
- Execution control (`RUN/STEP/STOP`) and state inspection (`READ_REGS/READ_MEM/STATUS`).
- Replacement of placeholder external E2E checks with real binary execution E2E.
- Migration/removal of host-assisted RV pipeline from active path.

Out of scope:
- Runtime VM rewrite.
- New ISA beyond agreed RV subset for this phase.

## 4. Target Runtime Architecture

1. Runtime VM executes copy-space program containing RV emulator service loop.
2. Host launcher only:
   - starts Runtime VM,
   - loads emulator image,
   - sends raw guest binary and control commands over channel ABI,
   - reads back result state.
3. RV instruction semantics are executed only by emulator logic inside space.

## 5. Phase Plan

## Phase A: Freeze Contract and Runtime Interface

Deliverables:
- Freeze ABI for in-space RV service commands:
  - `LOAD_CODE`
  - `RUN`
  - `STEP`
  - `STOP`
  - `STATUS`
  - `READ_REGS`
  - `READ_MEM`
  - `WRITE_MEM` (optional for debug, mandatory if needed by tests)
- Command/response schema versioned and documented.

Acceptance:
- ABI doc updated and tagged as migration contract baseline.

## Phase B: In-Space RV Emulator Service MVP

Deliverables:
- Emulator loop in space that fetches/decodes/executes RV32 subset required by SHA-256 test binary.
- Internal emulator state in space memory (PC, regs, flags, fault/stop reason).
- Channel handler dispatch for control operations.

Acceptance:
- `LOAD_CODE + RUN + READ_REGS` works with at least one non-trivial RV binary.

## Phase C: Remove Host-Assisted Runtime Path

Deliverables:
- Runtime path no longer depends on:
  - host trace->F0 conversion for RV execution,
  - host RV emulator for correctness in the execution path.
- Existing host-assisted scripts moved to legacy area and marked non-production.

Required migration actions:
- Move scripts/docs/tests tied to host RV translation/emulation from active gates to `legacy/` (or equivalent legacy namespace).
- Mark deprecated entrypoints with explicit "not part of in-space runtime path".

Acceptance:
- Active release/test gates for RV execution do not invoke host RV translation/emulation components.

## Phase D: Replace Placeholder/Stub External E2E

Deliverables:
- Replace infrastructure-only external E2E checks with real execution E2E:
  - load real external RV binaries,
  - execute via in-space emulator,
  - assert deterministic architectural outcomes.

Acceptance:
- External E2E tests fail if emulator semantics regress.
- No "infrastructure present" stubs remain in active RV execution gates.

## Phase E: SHA-256 Binary E2E as Release Gate

Deliverables:
- One canonical SHA-256 RV binary e2e test:
  - guest binary provided as raw RV binary artifact,
  - loaded via ABI `LOAD_CODE`,
  - executed via `RUN`/`STEP`,
  - digest validated via `READ_REGS` and/or `READ_MEM`.
- Zero dependence on host-side RV emulation for expected result computation in runtime path.

Acceptance:
- Test passes in clean environment with only 3-binary contract artifacts.

## Phase F: Final Cleanup and Enforcement

Deliverables:
- CI/release gate enforcing completion contract section 2.
- Legacy assets isolated and excluded from active release path.
- Documentation aligned to runtime reality.

Acceptance:
- Contract checks are machine-verifiable in CI.

## 6. Legacy Migration Policy

All host-assisted RV execution components must be either:
1. removed, or
2. moved under explicit legacy path with:
   - clear deprecation notice,
   - explicit exclusion from release gates,
   - no accidental invocation by default scripts.

## 7. Required Artifacts for Stage Closure

1. ABI spec (frozen for this stage).
2. In-space RV emulator binary/image artifact.
3. Guest SHA-256 RV test binary artifact.
4. One-command or minimal launcher invocation that uses only:
   - Runtime VM binary,
   - emulator image/binary,
   - guest binary.
5. CI evidence of passing hard-gate contract.

## 8. Non-Negotiable Stage Exit Criterion

Stage exits only when Section 2 (Completion Contract) is fully true.

Until then, stage status must remain: **in progress**.

