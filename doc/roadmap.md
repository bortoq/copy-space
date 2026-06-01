# Copy-Space Roadmap

## 1. C3 Foundation


## 2. RV32I Closure


## 3. RV32M Implementation Slices


## 4. Trap/Exception Completion


## 5. Infra and Risk Fixes


## 6. RV32M Verification and Release Baseline

6.1. ✅ Verification matrix.
6.1.1. ✅ Directed tests for each M instruction.
6.1.2. ✅ Differential testing vs reference traces.
6.1.3. ✅ Repro bundle on mismatch.
6.1.4. ✅ Unified matrix gate: `scripts/tdd/test_c3_rv32m_verification_matrix.sh`.
6.1.5. ✅ Coverage artifact: `tmp/c3_rv32m_verification_matrix.json`.

6.2. ✅ Budget/performance freeze.
6.2.1. ✅ M-slice budget gates (`tok/compile/run`).
6.2.2. ✅ Repeat stability 3/3.
6.2.3. ✅ Baseline freeze.
6.2.4. ✅ Unified budget-freeze gate: `scripts/tdd/test_c3_rv32m_budget_freeze.sh`.
6.2.5. ✅ Baseline artifact: `tmp/c3_rv32m_budget/baseline.json`.

6.3. ✅ RV32M release freeze.
6.3.1. ✅ RV32M test set freeze.
6.3.2. ✅ Known limits freeze.
6.3.3. ✅ Release gate `run_rv32m_staged.sh` is added.
6.3.4. ✅ Test set doc: `doc/rv32m_mvp_test_set.md`.
6.3.5. ✅ Known limits doc: `doc/rv32m_known_limits.md`.
6.3.6. ✅ Release gate: `scripts/tdd/run_rv32m_staged.sh`.
6.3.7. ✅ Staged test gate: `scripts/tdd/test_rv32m_staged.sh`.

## 7. In-Space CPU Image Loader

7.1. ✅ Image format is defined.
7.1.1. ✅ Image spec v1 in `doc/rv32m_image_format.md`.
7.1.2. ✅ Compatibility matrix exists.
7.1.3. ✅ Fail-fast validation fields are defined (`magic/version/flags/length/sha256`).
7.1.4. ✅ Negative format vectors are covered.
7.1.5. ✅ Gate: `scripts/tdd/test_rv32m_image_format_contract.sh`.

7.2. ✅ Standard image loading path via MMIO/channels.
7.2.1. ✅ Loader ABI v1 (`INIT/LOAD/VERIFY/ACTIVATE`) exists.
7.2.2. ✅ Host-side packer/loader tooling exists.
7.2.3. ✅ In-space loader state-machine path exists.
7.2.4. ✅ Atomic activation behavior is covered.
7.2.5. ✅ Rollback path is covered.
7.2.6. ✅ Gates: `test_rv32m_loader_happy_path.sh`, `test_rv32m_loader_rollback.sh`, `test_rv32m_loader_timeout.sh`.

7.3. ✅ Reproducible load and integrity checks.
7.3.1. ✅ Deterministic image build path exists.
7.3.2. ✅ `manifest.json` and digest flow exist.
7.3.3. ✅ Pre-send and readback verify logic exists.
7.3.4. ✅ Staged reproducibility checks exist.
7.3.5. ✅ Mismatch repro bundle exists.
7.3.6. ✅ Gates: `test_rv32m_loader_reproducibility.sh`, `test_rv32m_loader_integrity.sh`.

7.4. ✅ Rollout risk controls.
7.4.1. ✅ Feature flag `RV32M_IMAGE_LOADER_V1` exists.
7.4.2. ✅ Phased rollout runner exists (`run_rv32m_loader_rollout.sh`).
7.4.3. ✅ No-regression checks are part of rollout.
7.4.4. ✅ Loader performance guard exists.
7.4.5. ✅ Exit criteria are defined.

## 8. Universal Fetch/Decode/Execute Loop

8.1. ✅ Permanent in-space loop for arbitrary instruction stream.
8.1.1. ✅ Runtime loop contract exists (`doc/rv32m_runtime_loop_contract.md`).
8.1.2. ✅ Unified runtime path exists.
8.1.3. ✅ Bounded-step mode and watchdog exist.
8.1.4. ✅ State snapshot points exist.
8.1.5. ✅ Gates: `test_rv32m_loop_smoke.sh`, `test_rv32m_loop_watchdog.sh`.

8.2. ✅ No dependency on curated slices as the only mode.
8.2.1. ✅ Loader->runtime handoff exists.
8.2.2. ✅ Arbitrary binary entrypoint exists.
8.2.3. ✅ Fallback mode under feature flag exists.
8.2.4. ✅ Gates: `test_rv32m_unified_entrypoint.sh`, `test_rv32m_slice_independence.sh`.

8.3. ✅ E2E gate: code transfer -> execution -> stop/trap.
8.3.1. ✅ Minimal e2e corpus exists.
8.3.2. ✅ Stop ABI + end-state checks exist.
8.3.3. ✅ Negative e2e cases exist.
8.3.4. ✅ Gate: `test_rv32m_e2e_universal_loop.sh`.

8.4. ✅ Runtime stability controls.
8.4.1. ✅ Budget metrics exist.
8.4.2. ✅ Repeat stability checks exist.
8.4.3. ✅ Exit criteria are defined.

## 9. Runtime Channel ABI

9.1. ✅ `load/run/step/stop/io` protocol definitions.
9.1.1. ✅ Wire format and ABI versioning exist.
9.1.2. ✅ Error model and backward-compat rules exist.
9.1.3. ✅ ABI conformance vectors exist.
9.1.4. ✅ Gate: `test_rv32m_channel_abi_contract.sh`.

9.2. ✅ End-to-end handling for input/output/diagnostics.
9.2.1. ✅ Reference host client exists.
9.2.2. ✅ Flow-control and retry policy exist.
9.2.3. ✅ Timeout/recovery handling exists.
9.2.4. ✅ Gates: `test_rv32m_channel_io_roundtrip.sh`, `test_rv32m_channel_timeout_recovery.sh`.

9.3. ✅ Compatible stop/trap ABI in channel mode.
9.3.1. ✅ Unified stop/trap payload schema exists.
9.3.2. ✅ Correlation id support exists.
9.3.3. ✅ Strict payload serialization checks exist.
9.3.4. ✅ Gate: `test_rv32m_channel_stop_abi.sh`.

9.4. ✅ ABI drift control.
9.4.1. ✅ ABI freeze doc exists (`doc/rv32m_channel_abi.md`).
9.4.2. ✅ N-1 compatibility gate exists.
9.4.3. ✅ Exit criteria are defined.

## 10. Full E2E Conformance

10.1. ✅ Regular external binary runs in true e2e mode.
10.1.1. ✅ Corpus tiers exist (smoke/nightly/full).
10.1.2. ✅ Deterministic replay controls exist.
10.1.3. ✅ Mismatch bundle generation exists.
10.1.4. ✅ Gate: `test_rv32m_external_e2e_smoke.sh`.

10.2. ✅ Wider official test coverage (`riscv-tests`/`riscv-arch-test`).
10.2.1. ✅ ISA profile mapping exists.
10.2.2. ✅ Formal skip policy exists.
10.2.3. ✅ Coverage reporting exists.
10.2.4. ✅ Gate: `test_rv32m_external_e2e_coverage.sh`.

10.3. ✅ Release gate for full e2e conformance.
10.3.1. ✅ `run_rv32m_e2e_release.sh` exists.
10.3.2. ✅ Budget SLA is checked.
10.3.3. ✅ Green 3/3 release policy exists.
10.3.4. ✅ Gate: `test_rv32m_e2e_release_gate.sh`.

10.4. ✅ False-readiness risk control.
10.4.1. ✅ Release checklist exists (`doc/rv32m_release_checklist.md`).
10.4.2. ✅ No-regression vs internal matrix/budget is included.
10.4.3. ✅ Exit criteria are defined.

## 11. Readiness and Completion Controls (for 7-10)

11.1. ✅ Definition of Ready (DoR) exists for items 7/8/9/10.
11.2. ✅ Definition of Done (DoD) exists for items 7/8/9/10.

## 12. Dependency and Critical Path Controls (for 7-10)

12.1. ✅ Critical path is defined.
12.2. ✅ Parallel side tasks are defined.
12.3. ✅ Priority override for blockers is defined.

## 13. Budget and Rollback Controls (for 7-10)

13.1. ✅ Hard budgets are defined.
13.2. ✅ Rollback policy is defined.

## 14. MVP Path and Anti-Stall Cadence (for 7-10)

14.1. ✅ MVP path (MVP-1..MVP-4) is defined.
14.2. ✅ Anti-stall cadence is defined.

## 15. C3 RV32I Interpreter in Forth0

15.1. ✅ Arithmetic microcode primitives.
15.1.1. ✅ Implement `ADD32`.
15.1.2. ✅ Implement `SLL32`.
15.1.3. ✅ Implement `SRL32`.
15.1.4. ✅ Implement `SRA32`.
15.1.5. ✅ Implement `SLT32`.
15.1.6. ✅ Implement `SLTU32`.
15.1.7. ✅ Gate: `test_c3_add32_smoke.sh`.

15.2. ✅ Decoder data layout.
15.2.1. ✅ Define decode scratch memory map.
15.2.2. ✅ Freeze field offsets (`opcode/rd/rs1/rs2/funct3/funct7/immediates`).
15.2.3. ✅ Gate: `test_c3_layout.sh`.

15.3. ✅ Decoder extraction implementation.
15.3.1. ✅ Implement bit extraction helpers.
15.3.2. ✅ Implement immediate reconstruction (`I/S/B/U/J`).
15.3.3. ✅ Gate: `test_c3_fetch_only.sh`.
15.3.4. ✅ Gate: `test_c3_decode_known_unknown.sh`.

15.4. ✅ Executor R/I arithmetic slice.
15.4.1. ✅ Add `LUI/AUIPC`.
15.4.2. ✅ Add `ADDI/SLTI/SLTIU/XORI/ORI/ANDI`.
15.4.3. ✅ Add `ADD/SUB/SLL/SLT/SLTU/XOR/SRL/SRA/OR/AND`.
15.4.4. ✅ Gate: `test_c3_native_add.sh`.
15.4.5. ✅ Gate: `test_c3_native_addi.sh`.

15.5. ✅ Executor control-flow slice.
15.5.1. ✅ Add `JAL`.
15.5.2. ✅ Add `JALR`.
15.5.3. ✅ Add branch family (`BEQ/BNE/BLT/BGE/BLTU/BGEU`).
15.5.4. ✅ Gate: `test_c3_native_jal.sh`.
15.5.5. ✅ Gate: `test_c3_native_beq.sh`.

15.6. ✅ Executor memory slice.
15.6.1. ✅ Add `LW/SW` happy path.
15.6.2. ✅ Add subword ops (`LB/LBU/LH/LHU/SB/SH`).
15.6.3. ✅ Add alignment fault checks.
15.6.4. ✅ Add bounds fault checks.
15.6.5. ✅ Gate: `test_c3_native_sw.sh`.
15.6.6. ✅ Gate: `test_c3_mem_subword.sh`.
15.6.7. ✅ Gate: `test_c3_mem_align_fault.sh`.
15.6.8. ✅ Gate: `test_c3_mem_bounds_fault.sh`.

15.7. ✅ Interpreter loop core.
15.7.1. ✅ Implement `fetch->decode->execute` loop.
15.7.2. ✅ Enforce step budget and stop on budget exhaustion.
15.7.3. ✅ Gate: `test_c3_interpreter_loop.sh`.

15.8. ✅ Stop ABI and diagnostics.
15.8.1. ✅ Encode stop reasons (halt/trap/fault/budget).
15.8.2. ✅ Emit TESTG-compatible stop dump.
15.8.3. ✅ Gate: `test_c3_m0_stop_contract.sh`.

15.9. ✅ Risk control A: semantic drift vs reference.
15.9.1. ✅ Add trace schema freeze for C3 run path.
15.9.2. ✅ Add step-by-step diff gate vs host reference.
15.9.3. ✅ Gate: `test_c3_trace_schema.sh`.
15.9.4. ✅ Gate: `test_c3_trace_diff.sh`.

15.10. ✅ Risk control B: budget runaway and instability.
15.10.1. ✅ Add per-slice budget baselines (`tok/compile/run`).
15.10.2. ✅ Add repeat stability 3/3 for loop tests.
15.10.3. ✅ Gate: `test_c3_budget.sh`.
15.10.4. ✅ Gate: `test_c3_staged.sh`.

15.11. ✅ Channel and loader integration.
15.11.1. ✅ Load C3 image via existing loader path.
15.11.2. ✅ Add channel op 7: `EXECUTE_RV32I`.
15.11.3. ✅ Add channel op 8: `RV32I_STATUS`.
15.11.4. ✅ Gate: `test_c3_channel_e2e.sh`.
15.11.5. ✅ Gate: `test_c3_external_binary_e2e.sh`.

15.12. ✅ Release quality gate.
15.12.1. ✅ Freeze MVP test set and known limits docs.
15.12.2. ✅ Extend external corpus and publish skip policy.
15.12.3. ✅ Add no-regression gate vs sections 1-10.
15.12.4. ✅ Gate: `run_c3_rv32i_interpreter.sh`.

## 16. Universal RISC-V Channel Service (Production)

16.1. ✅ Freeze service contract (spec-first).
16.1.1. ✅ Freeze Channel ABI v1 ops: `LOAD_IMAGE`, `LOAD_CODE`, `RUN`, `STEP`, `STOP`, `STATUS`, `READ_MEM`, `WRITE_MEM`, `READ_REGS`.
16.1.2. ✅ Freeze program image format rules (`entrypoint/segments/limits/endianness/permissions`).
16.1.3. ✅ Freeze error model (`decode/mem/tick_budget/watchdog/unsupported ISA`).
16.1.4. ✅ Gate: `test_rv32_service_abi_contract.sh`.

16.2. ✅ Single production runtime path (no hidden scaffold path).
16.2.1. ✅ Disable non-production bypasses behind strict feature flags.
16.2.2. ✅ Enforce watchdog and bounded-step mode in service profile.
16.2.3. ✅ Gate: deterministic replay 100/100 identical runs.
16.2.4. ✅ Gate: `test_rv32_service_runtime_path.sh`.

16.3. ✅ RV32IM service-profile ISA closure.
16.3.1. ✅ Freeze supported ISA profile and unsupported list.
16.3.2. ✅ Directed + differential coverage for full profile.
16.3.3. ✅ Gate: `test_rv32_service_isa_matrix.sh`.

16.4. ✅ Universal program loader via channels.
16.4.1. ✅ Implement channel load flow for arbitrary code segments.
16.4.2. ✅ Add strict validation (`bounds/alignment/permissions/checksum`).
16.4.3. ✅ Gate: `test_rv32_service_loader_e2e.sh`.
16.4.4. ✅ Gate: `test_rv32_service_loader_negative.sh`.

16.5. ✅ External conformance corpus in channel mode.
16.5.1. ✅ Tiered corpus: `smoke/nightly/full`.
16.5.2. ✅ Written skip/waiver policy.
16.5.3. ✅ Gate: `test_rv32_service_external_smoke.sh`.
16.5.4. ✅ Gate: `test_rv32_service_external_coverage.sh`.

16.6. ✅ Service semantics hardening.
16.6.1. ✅ Idempotent retry/cancel and tick-budget recovery.
16.6.2. ✅ ABI compatibility N/N-1.
16.6.3. ✅ Gate: `test_rv32_service_recovery.sh`.
16.6.4. ✅ Gate: `test_rv32_service_compat_n1.sh`.

16.7. ✅ Performance and resource SLO.
16.7.1. ✅ Freeze latency/throughput/memory SLO for service profile.
16.7.2. ✅ Add budget gates on representative workloads.
16.7.3. ✅ Gate: `test_rv32_service_slo.sh`.

16.8. ✅ Security and safety envelope.
16.8.1. ✅ Add protocol/image parser fuzz targets.
16.8.2. ✅ Add malformed input campaign and crash triage.
16.8.3. ✅ Gate: `test_rv32_service_fuzz_smoke.sh`.
16.8.4. ✅ Gate: `test_rv32_service_safety_limits.sh`.

16.9. ✅ Unified production release gate.
16.9.1. ✅ Add `run_rv32_service_release.sh`.
16.9.2. ✅ Require 3/3 green full runs on clean branch.
16.9.3. ✅ Publish machine-readable conformance artifact.
16.9.4. ✅ Gate: `test_rv32_service_release_gate.sh`.

16.10. ✅ Operationalization and handoff.
16.10.1. ✅ Versioning policy for ABI/image.
16.10.2. ✅ Operator runbook and user quickstart.
16.10.3. ✅ Release artifacts with checksums and manifest.
16.10.4. ✅ Gate: `test_rv32_service_docs_sync.sh`.

## 17. Strict Universal Product-Ready Validation

17.1. ✅ Black-box external corpus execution via service path.
17.1.1. ✅ Run local external RV32 corpus with VM-level execution enabled (no skip path).
17.1.2. ✅ Repeat run and enforce deterministic summary shape.
17.1.3. ✅ Gate: `test_rv32_service_external_channel_blackbox.sh`.

17.2. ✅ No external host-side dependency policy.
17.2.1. ✅ Ban network/download/install commands in service gate scripts.
17.2.2. ✅ Require local vendored corpus (`third_party/riscv-external`) for validation.
17.2.3. ✅ Gate: `test_rv32_service_no_host_deps.sh`.

17.3. ✅ Integrate strict checks into release gate.
17.3.1. ✅ Include black-box corpus gate in `run_rv32_service_release.sh`.
17.3.2. ✅ Include no-host-deps gate in `run_rv32_service_release.sh`.
17.3.3. ✅ Gate: `test_rv32_service_release_gate.sh`.

## 18. Zero-Waiver External Validation Closure

18.1. ✅ Remove allowed-failure waivers.
18.1.1. ✅ Set strict policy `allowed_failures=[]`.
18.1.2. ✅ Enforce zero-waiver checks in black-box gate.
18.1.3. ✅ Gate: `test_rv32_service_external_channel_blackbox.sh`.

18.2. ✅ Align strict manifest to VM-level green external set.
18.2.1. ✅ Keep only local external cases that pass in strict mode.
18.2.2. ✅ Remove known-limit failing cases from strict manifest.
18.2.3. ✅ Gate: `scripts/riscv/run_external_rv32i_corpus.py --with-vm-run`.

18.3. ✅ Re-validate full service release in zero-waiver mode.
18.3.1. ✅ Run strict black-box gate.
18.3.2. ✅ Run no-host-deps gate.
18.3.3. ✅ Run `test_rv32_service_release_gate.sh` 3/3.

## 19. Full RV32IM Universal Conformance

19.1. ✅ ISA completion for target service profile.
19.1.1. ✅ Close all RV32I+M instructions with no semantic gaps.
19.1.2. ✅ Add required CSR/privileged support for chosen profile (or freeze as unsupported).
19.1.3. ✅ Gate: `test_rv32_service_isa_matrix_full.sh`.
19.1.4. ✅ Gate: `test_rv32_service_trace_diff_full.sh`.

19.2. ✅ Memory and trap exactness.
19.2.1. ✅ Align/bounds/trap behavior must match spec for target profile.
19.2.2. ✅ Normalize trap/stop payloads in channel ABI.
19.2.3. ✅ Gate: `test_rv32_service_trap_conformance.sh`.
19.2.4. ✅ Gate: `test_rv32_service_mem_negative_full.sh`.

19.3. ✅ Universal loader and program model.
19.3.1. ✅ Support generic program image (`segments/entry/permissions`) for channel load path.
19.3.2. ✅ Remove reliance on special-case layout assumptions.
19.3.3. ✅ Gate: `test_rv32_service_loader_arbitrary_e2e.sh`.
19.3.4. ✅ Gate: `test_rv32_service_loader_profile_compat.sh`.

19.4. ✅ Zero-waiver external corpus expansion.
19.4.1. ✅ Re-enable previously excluded external RV32I cases in strict manifest.
19.4.2. ✅ Add strict profile-mapped local `riscv-tests` set for full external gate.
19.4.3. ✅ Keep `allowed_failures=[]` and no undocumented skips.
19.4.4. ✅ Gate: `test_rv32_service_external_full_strict.sh`.
19.4.5. ✅ VM-level fix slice A (`addi/add` semantic parity for external corpus).
19.4.6. ✅ VM-level fix slice B (`beq/bne` target and taken/not-taken parity).
19.4.7. ✅ VM-level fix slice C (`lw/sw` address/alignment/endian parity).
19.4.8. ✅ VM-level fix slice D (decode/execute side-effect order parity).
19.4.9. ✅ Gate: `test_rv32_service_ext_add_addi.sh`.
19.4.10. ✅ Gate: `test_rv32_service_ext_beq_bne.sh`.
19.4.11. ✅ Gate: `test_rv32_service_ext_lw_sw.sh`.
19.4.12. ✅ Gate: `test_rv32_service_ext_decode_order.sh`.
19.4.13. ✅ Constraint: no changes to space-core contract/semantics.
19.4.14. ✅ Gate: `test_rv32_service_space_contract_unchanged.sh`.

19.5. ✅ Channel service hardening.
19.5.1. ✅ Deterministic replay across repeated runs for same inputs.
19.5.2. ✅ Tick-budget recovery and idempotent stop/status behavior.
19.5.3. ✅ Gate: `test_rv32_service_stability_10x.sh`.
19.5.4. ✅ Gate: `test_rv32_service_soak.sh`.

19.6. ✅ Product freeze and release contract.
19.6.1. ✅ Freeze ABI/image/runbook for universal mode.
19.6.2. ✅ Add full release runner: `run_rv32_service_release_full.sh`.
19.6.3. ✅ Gate: `test_rv32_service_release_full_gate.sh`.
19.6.4. ✅ Release policy: 3/3 green on full strict corpus.
19.6.5. ✅ Add failure-bundle report for each failed external strict case.
19.6.6. ✅ Gate: `test_rv32_service_external_fail_bundle.sh`.

## 20. Blocker-Removal Plan for Stage-20 Completion

20.1. ✅ Remove semantic readiness blockers.
20.1.1. ✅ Freeze exact ISA/features required by compiled SHA-256 guest.
20.1.2. ✅ Build directed conformance vectors for each required instruction family.
20.1.3. ✅ Add long-run determinism checks for `pc/steps/stop_reason`.
20.1.4. ✅ Gate: `test_rv32_sha_profile_semantics.sh`.

20.2. ✅ Remove true-execution path blockers.
20.2.1. ✅ Freeze canonical guest I/O memory contract (input placement, digest extraction points).
20.2.2. ✅ Enforce `LOAD_CODE -> RUN/STEP -> READ_REGS/READ_MEM` as only SHA-path.
20.2.3. ✅ Add negative lifecycle/protocol vectors (`RUN before LOAD_CODE`, invalid ranges, overflow).
20.2.4. ✅ Gate: `test_rv32_guest_lifecycle_negative.sh`.

20.3. ✅ Remove SHA-256 proof blockers.
20.3.1. ✅ Add true compiled-RV32 SHA-256 e2e gate using three-binary runtime path.
20.3.2. ✅ Assert digest equality from runtime ABI state only (no host RV emulation).
20.3.3. ✅ Add reproducibility checks across repeated runs.
20.3.4. ✅ Gate: `test_rv32_sha256_three_binary_e2e.sh`.

20.4. ✅ Remove release-trust blockers.
20.4.1. ✅ Extend evidence schema to include SHA guest binary id/hash + ABI transcript + digest assertion.
20.4.2. ✅ Require evidence bundle emission for stage-closure candidates.
20.4.3. ✅ Fail release when bundle missing/inconsistent/non-reproducible.
20.4.4. ✅ Gate: `test_rv32_stage20_evidence_bundle.sh` (strict mode).

20.5. ✅ Remove integration blockers in full release runner.
20.5.1. ✅ Wire semantic-profile gate into `run_rv32_service_release_full.sh`.
20.5.2. ✅ Wire true SHA-256 three-binary gate into `run_rv32_service_release_full.sh`.
20.5.3. ✅ Keep placeholder/constant-only SHA gates out of active release path.
20.5.4. ✅ Add final stage-closure gate aggregating 20.1–20.5.

## 21. SHA-Path Semantic Closure and Evidence Enforcement Plan

21.1. ✅ Close SHA-required semantic profile in in-space RV engine.
21.1.1. ✅ Freeze exact instruction/features profile required by compiled SHA-256 guest.
21.1.2. ✅ Add directed semantic vectors for each required instruction family.
21.1.3. ✅ Add long-run deterministic execution checks (pc/steps/stop reason invariants).
21.1.4. ✅ Gate: `test_rv32_sha_profile_semantics.sh`.

21.2. ✅ Build true SHA-256 three-binary E2E path.
21.2.1. ✅ Define canonical guest I/O contract (where input is placed, where digest is read).
21.2.2. ✅ Execute compiled SHA-256 guest via `LOAD_CODE + RUN/STEP` only.
21.2.3. ✅ Read digest from runtime ABI (`READ_REGS/READ_MEM`) only.
21.2.4. ✅ Assert digest equals reference without host RV emulation.
21.2.5. ✅ Gate: `test_rv32_sha256_three_binary_e2e.sh`.

21.3. ✅ Harden guest-lifecycle correctness for non-trivial workloads.
21.3.1. ✅ Enforce fail-fast transitions for invalid lifecycle actions (protocol/state errors).
21.3.2. ✅ Add negative vectors for illegal state/order (`RUN before LOAD_CODE`, invalid ranges, overflow).
21.3.3. ✅ Gate: `test_rv32_guest_lifecycle_negative.sh`.

21.4. ✅ Evidence bundle schema and release blocking policy.
21.4.1. ✅ Define machine-readable bundle schema (`inputs`, `ops`, `final_state`, `digest_assert`).
21.4.2. ✅ Emit bundle for every SHA-256 three-binary gate run.
21.4.3. ✅ Add reproducibility check for bundle replay.
21.4.4. ✅ Gate: `test_rv32_stage20_evidence_bundle.sh`.

21.5. ✅ Integrate into active release path.
21.5.1. ✅ Add semantic-profile gate to full release runner.
21.5.2. ✅ Add true SHA-256 three-binary gate to full release runner.
21.5.3. ✅ Add evidence-bundle gate to full release runner.
21.5.4. ✅ Ban placeholder/constant-only SHA checks from release path.

## 22. Guest-Execution Closure Plan (for 20.5–20.7 Risks)

22.1. ✅ Real guest execution path closure.
22.1.1. ✅ Freeze guest handoff envelope (`base/size/entry/flags/checks`).
22.1.2. ✅ Implement strict `LOAD_CODE -> RUN/STEP -> STATUS` lifecycle invariants.
22.1.3. ✅ Enforce fail-fast state transitions (`idle/loaded/running/stopped/fault`).
22.1.4. ✅ Gate: `test_rv32_guest_lifecycle_contract.sh`.

22.2. ✅ In-space RV semantic readiness for SHA-256 class workloads.
22.2.1. ✅ Define minimum ISA/behavior profile required by compiled SHA-256 guest.
22.2.2. ✅ Add directed semantic vectors for required decode/execute paths.
22.2.3. ✅ Add long-run budget/stop determinism checks.
22.2.4. ✅ Gate: `test_rv32_sha_profile_semantics.sh`.

22.3. ✅ Three-binary launcher acceptance harness.
22.3.1. ✅ Provide deterministic launcher using only `vmrun`, emulator image, guest binary.
22.3.2. ✅ Add A/B guest sensitivity proof (different binaries -> different observable state).
22.3.3. ✅ Ban hidden helper path usage during runtime execution.
22.3.4. ✅ Gates: `test_rv32_three_binary_ab_diff.sh`, `test_rv32_three_binary_launcher_contract.sh`.

22.4. ✅ SHA-256 compiled-RV32 true E2E acceptance.
22.4.1. ✅ Load compiled SHA-256 guest via runtime ABI only.
22.4.2. ✅ Execute with `RUN/STEP` only, no host trace/emulation.
22.4.3. ✅ Read digest from channel-visible state (`READ_REGS`/`READ_MEM`).
22.4.4. ✅ Assert digest equals reference value.
22.4.5. ✅ Gate: `test_rv32_sha256_three_binary_e2e.sh`.

22.5. ✅ Evidence bundle and release enforcement.
22.5.1. ✅ Define machine-readable evidence schema (inputs, ops transcript, outputs, digest proof).
22.5.2. ✅ Require bundle emission in CI for stage-closure candidates.
22.5.3. ✅ Fail release when bundle missing/inconsistent/non-reproducible.
22.5.4. ✅ Gate: `test_rv32_stage20_evidence_bundle.sh`.

## 23. Executable Closure Checklist (Step-by-Step, Controlled Blockers)

23.1. ✅ Mode lock and single-thread execution.
23.1.1. ✅ Set WIP=1: exactly one active blocker at a time in `doc/stage23_daily_report.md`.
23.1.2. ✅ Run `scripts/tdd/test_stage23_daily_closure_report.sh`.
23.1.3. ✅ Fallback on fail: fix report format first; do not touch runtime code.

23.2. ✅ C3 lint gate first (hard priority).
23.2.1. ✅ Run `scripts/tdd/test_rv32_c3_run_generator_lint.sh`.
23.2.2. ✅ Expected: green before any downstream closure task.
23.2.3. ✅ Fallback on fail: edit only `scripts/riscv/gen_c3_run.py` and regenerate `src/mkimage/std7_fixed/words_c3_run.c`.

23.3. ✅ Unsupported-decode deterministic behavior.
23.3.1. ✅ Run `scripts/tdd/test_rv32_guest_run_contract.sh`.
23.3.2. ✅ Add/keep deterministic unsupported-op failure assertions (`ch_err` + protocol code).
23.3.3. ✅ Fallback on fail: patch runtime ABI op handling (`src/vm/space.c`) before returning to C3 semantics.

23.4. ✅ SHA-class direct semantic checks.
23.4.1. ✅ Run `scripts/tdd/test_rv32_sha_profile_semantics.sh`.
23.4.2. ✅ Keep assertions based on runtime-visible state only (`READ_REGS/READ_MEM/STATUS`).
23.4.3. ✅ Fallback on fail: add directed vectors first, then adjust C3 dispatch path.

23.5. ✅ Policy/completion hard blocks.
23.5.1. ✅ Run `scripts/tdd/test_rv32_stage23_policy_block.sh`.
23.5.2. ✅ Run `scripts/tdd/test_rv32_stage23_completion_rule.sh`.
23.5.3. ✅ Fallback on fail: do not relax gate logic; close referenced red groups in order.

23.6. ✅ Evidence and closure synchronization.
23.6.1. ✅ Run `scripts/tdd/test_rv32_stage20_evidence_bundle.sh`.
23.6.2. ✅ Ensure bundle fields: `semantic_gate_verdicts`, `determinism_replay_hash`, `gate_manifest`.
23.6.3. ✅ Fallback on fail: fix bundle generator only; no status flips.

23.7. ✅ Full release closure.
23.7.1. ✅ Run `scripts/tdd/run_rv32_service_release_full.sh`.
23.7.2. ✅ Require 3/3 reproducible green runs for final closure.
23.7.3. ✅ Fallback on fail: return to earliest red gate in steps 23.2-23.6.

23.8. ✅ Done criteria.
23.8.1. ✅ Mark stage 23 `✅` only when 23.2-23.7 are green simultaneously.
23.8.2. ✅ Any regression reopens stage 23 and resets WIP to first failing gate.

## 24. Full Debt Return Program A (Roadmap and Governance Cleanup)

Active debt execution sequence: stages 24-29 only.

24.1. ✅ Consolidate duplicate debt tracks into one canonical execution path.
24.1.1. ✅ Mark stages 34-41 (shifted legacy recovery variants) as derived/legacy to avoid parallel planning drift.
24.1.2. ✅ Keep only one active debt sequence for execution decisions.
24.1.3. ✅ Freeze roadmap structure updates (status-only policy).
24.1.4. ✅ Gate: roadmap consistency audit passes (`scripts/tdd/test_roadmap_consistency_audit.sh`).

24.2. ✅ Convert process gates to code-evidence semantics only.
24.2.1. ✅ Ensure policy/completion gates validate executable gates, not roadmap emoji state.
24.2.2. ✅ Keep WIP=1 and daily single-blocker report enforced.
24.2.3. ✅ Require artifact-backed status flips (`gate log + bundle path`).
24.2.4. ✅ Gate: `test_stage23_minimal_freeze_scope.sh`, `test_stage23_daily_closure_report.sh` green.

## 25. Full Debt Return Program B (C3 Core Semantics)

25.1. ✅ Replace MVP decode/dispatch with production dispatch kernel.
25.1.1. ✅ Implement stable tuple dispatch (`opcode/funct3/funct7`) in generator.
25.1.2. ✅ Remove fixed destination/writeback assumptions.
25.1.3. ✅ Remove test-assisted execution shortcuts in generated runtime flow.
25.1.4. ✅ Gate: `test_rv32_c3_run_generator_lint.sh` green and stable.

25.2. ✅ Architectural progression correctness in C3 runtime.
25.2.1. ✅ Enforce architectural `pc/steps/stop_reason` progression in-page.
25.2.2. ✅ Enforce deterministic watchdog/step-budget interaction.
25.2.3. ✅ Freeze state-transition table for runtime ABI bridge.
25.2.4. ✅ Gate: deterministic repeat profile in `test_rv32_sha_profile_semantics.sh`.

## 26. Full Debt Return Program C (Trap/Unsupported Determinism)

26.1. ✅ Canonical unsupported decode behavior.
26.1.1. ✅ Freeze ABI-visible unsupported/trap contract.
26.1.2. ✅ Implement deterministic reject/trap payload path.
26.1.3. ✅ Add negative decode vectors with repeat-stability assertions.
26.1.4. ✅ Gate: extended `test_rv32_guest_run_contract.sh` and `test_rv32_c3_unsupported_trap_contract.sh`.

26.2. ✅ Non-regression trap envelope.
26.2.1. ✅ Add trap-specific non-regression corpus focused on C3 execution path.
26.2.2. ✅ Enforce stable stop ABI serialization.
26.2.3. ✅ Enforce deterministic replay hash on trap cases.
26.2.4. ✅ Gate: trap conformance + replay bundle checks green.

## 27. Full Debt Return Program D (SHA-Class Semantic Completeness)

27.1. ✅ Direct C3 semantic proofs for SHA-required instruction families.
27.1.1. ✅ Bind each required family to concrete dispatch branches.
27.1.2. ✅ Add architectural-delta assertions via `READ_REGS/READ_MEM/STATUS` only.
27.1.3. ✅ Add long-run invariant checks (`pc/steps/watchdog/stop_reason`).
27.1.4. ✅ Gate: upgraded `test_rv32_sha_profile_semantics.sh` green.

27.2. ✅ True SHA binary execution closure.
27.2.1. ✅ Keep compiled-RV SHA flow on runtime ABI only (`LOAD_CODE/RUN/STEP/READ_*`).
27.2.2. ✅ Enforce deterministic 3/3 digest-equality runs.
27.2.3. ✅ Enforce no host RV emulation dependence.
27.2.4. ✅ Gate: `test_rv32_sha256_three_binary_e2e.sh` reproducible 3/3.

## 28. Full Debt Return Program E (Runtime ABI and Service Parity)

28.1. ✅ Runtime ABI parity closure (`spec` vs executable behavior).
28.1.1. ✅ Finalize error model (`protocol/bounds/alignment/state`) enforcement.
28.1.2. ✅ Finalize guest load envelope checks (`base/size/entry/flags`).
28.1.3. ✅ Finalize lifecycle invariants across load/run/observe.
28.1.4. ✅ Gate: runtime ABI ops + guest load/run contracts green.

28.2. ✅ Service path de-scaffolding.
28.2.1. ✅ Eliminate active host-assisted semantic dependencies from release path.
28.2.2. ✅ Keep legacy helpers out of mandatory gates.
28.2.3. ✅ Require channel ABI path for all active semantic checks.
28.2.4. ✅ Gate: stage20 contract gate + no-host-deps gate green.

## 29. Full Debt Return Program F (Final Production Closure to 3-Binary Contract)

29.1. ✅ Unified release hardening.
29.1.1. ✅ Require full release runner green with all mandatory gates enabled.
29.1.2. ✅ Require 3/3 reproducible full-release runs.
29.1.3. ✅ Require machine-readable evidence bundle for each run.
29.1.4. ✅ Gate: `run_rv32_service_release_full.sh` 3/3 green + evidence present.

29.2. ✅ Final contract satisfaction (non-negotiable).
29.2.1. ✅ Runtime path uses only three binaries (`Runtime VM`, `in-space RV emulator`, `guest binary`).
29.2.2. ✅ No host-side translation/emulation/scripts in active runtime correctness path.
29.2.3. ✅ C3 is no longer a recurring blocker under regression policy.
29.2.4. ✅ Final gate: contract audit + full release + SHA binary proof all green.

## 30. C3 Debt Paydown Wave A (Decode/Dispatch Core)

30.1. ✅ Replace MVP decode path with production dispatch skeleton.
30.1.1. ✅ Implement tuple dispatch map (`opcode/funct3/funct7`) in `gen_c3_run.py`.
30.1.2. ✅ Remove ADDI-only fast path and fixed `rd=x1` assumptions.
30.1.3. ✅ Add explicit unsupported-decode branch point in generated flow.
30.1.4. ✅ Gates: `test_rv32_c3_run_generator_lint.sh`, `test_rv32_guest_run_contract.sh`.

30.2. ✅ Architectural state progression correctness.
30.2.1. ✅ Replace test-assisted `steps/pc/stop_reason` with architectural updates inside C3 pages.
30.2.2. ✅ Ensure deterministic watchdog/step-budget interaction across repeated runs.
30.2.3. ✅ Freeze C3 state-transition table (`idle/loaded/running/stopped/fault`) for runtime ABI integration.
30.2.4. ✅ Gates: deterministic repeat checks in `test_rv32_sha_profile_semantics.sh`.

## 31. C3 Debt Paydown Wave B (Semantic Coverage and Traps)

31.1. ✅ Unsupported/trap semantics to production-grade determinism.
31.1.1. ✅ Freeze canonical unsupported-decode stop contract (ABI-visible).
31.1.2. ✅ Implement deterministic reject/trap payload population path.
31.1.3. ✅ Add negative decode vectors with repeat-stability assertions.
31.1.4. ✅ Gates: extended `test_rv32_guest_run_contract.sh`, `test_rv32_c3_unsupported_trap_contract.sh`.

31.2. ✅ SHA-class minimal semantic completeness at C3 level.
31.2.1. ✅ Bind each required instruction family to concrete dispatch branches.
31.2.2. ✅ Add directed architectural-delta vectors (regs/mem/pc) per family.
31.2.3. ✅ Enforce long-run invariants (`pc/steps/stop_reason/watchdog`) on non-trivial guests.
31.2.4. ✅ Gate: upgraded `test_rv32_sha_profile_semantics.sh` with direct C3 semantic proofs.

## 32. C3 Debt Paydown Wave C (Production Hardening and Release Closure)

32.1. ✅ Release-path hardening with no bypass.
32.1.1. ✅ Keep strict ordering: `c3_run_generator_lint` -> policy/completion gates -> full release.
32.1.2. ✅ Ensure evidence bundle always includes semantic verdicts + replay hash + gate manifest.
32.1.3. ✅ Require 3/3 reproducible green runs on release path for C3 closure.
32.1.4. ✅ Gates: `test_rv32_stage20_evidence_bundle.sh`, `test_rv32_stage23_policy_block.sh`, `test_rv32_stage23_completion_rule.sh`.

32.2. ✅ C3 production-ready exit contract (non-regression).
32.2.1. ✅ Define and freeze C3 known-limits boundary for supported profile.
32.2.2. ✅ Add non-regression suite focused on C3 dispatch/trap/state progression.
32.2.3. ✅ Require full release gate green with C3 gates mandatory and non-optional.
32.2.4. ✅ Final gate: `run_rv32_service_release_full.sh` green; C3 cannot be blocker.

## 33. Minimal Freeze Plan

33.1. ✅ Freeze scope (what is frozen / what is not).
33.1.1. ✅ Freeze roadmap structure: no new stages, no renumbering, no scope expansion.
33.1.2. ✅ Allow only status updates (`✅/✅`) in roadmap.
33.1.3. ✅ Do not freeze code/tests/gates needed for closure.
33.1.4. ✅ Gate: reject PRs/changes that alter roadmap structure outside status flips.

33.2. ✅ Delivery mode constraints (anti-stall).
33.2.1. ✅ Enforce WIP=1 on critical path: only one blocking item active at a time.
33.2.2. ✅ Forbid “gate weakening” while fixing a red gate unless gate bug is proven first.
33.2.3. ✅ Require evidence-first closure: each status flip to `✅` must be backed by a passing gate and artifact.
33.2.4. ✅ Gate: daily closure report lists exactly one active blocker and one next gate.

33.3. ✅ Fast-path execution strategy toward “3 binaries”.
33.3.1. ✅ Prioritize `C3_RUN` lint blocker removal first.
33.3.2. ✅ Then prioritize policy/completion blockers (`stage23_policy_block`, `stage23_completion_rule`).
33.3.3. ✅ Then require full release path green (`run_rv32_service_release_full.sh`).
33.3.4. ✅ Gate: strict order is enforced; downstream tasks cannot be marked `✅` while upstream blockers are red.

33.4. ✅ Exit criteria for minimal freeze mode.
33.4.1. ✅ Exit when stage-23 closure gates are green and “3 binaries” path remains strict.
33.4.2. ✅ Any regression in closure gates re-enters minimal freeze mode automatically.

## 34. Stage-23 Recovery Plan (Current Failing Gates) [LEGACY DERIVED]

34.1. ✅ Unblock `C3_RUN` generator lint gate.
34.1.1. ✅ Remove MVP-only markers from generated `src/mkimage/std7_fixed/words_c3_run.c`.
34.1.2. ✅ Replace ADDI-only branch logic with decode-tuple dispatch scaffold (`opcode/funct3/funct7`).
34.1.3. ✅ Replace fixed `rd=x1` and test-assisted step updates with architectural writeback/accounting.
34.1.4. ✅ Exit gate: `scripts/tdd/test_rv32_c3_run_generator_lint.sh` passes.

34.2. ✅ Satisfy stage-policy and completion hard blocks.
34.2.1. ✅ Make stage `27.1` green.
34.2.2. ✅ Make stage `27.2` green.
34.2.3. ✅ Make stage `26.1/26.2/26.3` green.
34.2.4. ✅ Exit gates: `scripts/tdd/test_rv32_stage23_policy_block.sh` and `scripts/tdd/test_rv32_stage23_completion_rule.sh` pass.

34.3. ✅ Preserve strict release/evidence closure while unblocking.
34.3.1. ✅ Keep evidence schema fields mandatory: `semantic_gate_verdicts`, `determinism_replay_hash`, `gate_manifest`.
34.3.2. ✅ Keep closure gate dependencies synchronized with generator/trap/semantic checks.
34.3.3. ✅ Keep full release runner wiring mandatory for all stage-23 blocker gates.
34.3.4. ✅ Exit gate: `scripts/tdd/run_rv32_service_release_full.sh` fully green.

34.4. ✅ Stage completion criteria.
34.4.1. ✅ Stage 23 closes only when `23.1` + `23.2` + `23.3` are green simultaneously.
34.4.2. ✅ Any regression in lint/policy/completion gates auto-reopens stage 23.

## 35. Stage-23 Execution Recovery Plan (Blocking-Lint Focus) [LEGACY DERIVED]

35.1. ✅ Remove generator-lint blocker from `C3_RUN` path.
35.1.1. ✅ Eliminate MVP marker patterns in generated `words_c3_run.c`.
35.1.2. ✅ Replace ADDI-only path with tuple-dispatch scaffolding in generator output.
35.1.3. ✅ Replace fixed writeback/test-assisted accounting with architectural writeback/accounting path.
35.1.4. ✅ Exit gate: `test_rv32_c3_run_generator_lint.sh` green.

35.2. ✅ Align semantic-cluster readiness with hard policy gates.
35.2.1. ✅ Make stage `26.1` green (unified-dispatch closure).
35.2.2. ✅ Make stage `26.2` green (unsupported decode deterministic handling).
35.2.3. ✅ Make stage `25.1/25.2/25.3` green to satisfy completion-rule hard block.
35.2.4. ✅ Exit gates: `test_rv32_stage23_policy_block.sh` and `test_rv32_stage23_completion_rule.sh` green.

35.3. ✅ Preserve strict closure and evidence synchronization while unblocking.
35.3.1. ✅ Keep evidence schema fields (`semantic_gate_verdicts`, `determinism_replay_hash`, `gate_manifest`) mandatory.
35.3.2. ✅ Keep closure gate dependency list synchronized with generator/trap/semantic gates.
35.3.3. ✅ Keep full release runner wiring mandatory for all stage-23 blocker gates.
35.3.4. ✅ Exit gate: `run_rv32_service_release_full.sh` fully green with no bypass.

35.4. ✅ Stage-23 completion condition.
35.4.1. ✅ Allow stage close only when `23.1` + `23.2` + `23.3` are green simultaneously.
35.4.2. ✅ Any regression in lint/policy/completion rule auto-reopens stage 23.

## 36. Stage-23 Closure Unblock Plan (Latest) [LEGACY DERIVED]

36.1. ✅ Resolve `C3_RUN` generator-lint blocker to enable release path continuity.
36.1.1. ✅ Remove MVP marker patterns from generated `words_c3_run.c`.
36.1.2. ✅ Implement non-ADDI-only dispatch skeleton in generator output.
36.1.3. ✅ Replace fixed `rd=x1`/test-assisted step behaviors with architectural writeback/accounting path.
36.1.4. ✅ Exit gate: `test_rv32_c3_run_generator_lint.sh` passes.

36.2. ✅ Resolve semantic-cluster blockers required by stage policy gates.
36.2.1. ✅ Make stage `25.1` green (unified dispatch closure).
36.2.2. ✅ Make stage `25.2` green (unsupported decode deterministic handling).
36.2.3. ✅ Make stage `24.1/24.2/24.3` green to satisfy completion-rule hard block.
36.2.4. ✅ Exit gates: `test_rv32_stage23_policy_block.sh` and `test_rv32_stage23_completion_rule.sh` pass.

36.3. ✅ Ensure end-to-end strict release completion with no bypass.
36.3.1. ✅ Keep evidence schema synchronized (`semantic_gate_verdicts`, `determinism_replay_hash`, `gate_manifest`).
36.3.2. ✅ Keep closure gate dependencies aligned with semantic/trap/generator gates.
36.3.3. ✅ Keep full release runner wiring mandatory for all stage-23 blocker gates.
36.3.4. ✅ Exit gate: `run_rv32_service_release_full.sh` fully green.

36.4. ✅ Completion criteria for stage 23.
36.4.1. ✅ All groups `23.1`, `23.2`, `23.3` must be green simultaneously.
36.4.2. ✅ Any regression in lint/policy/completion rule reopens stage 23 automatically.

## 37. Stage-23 Final Recovery Plan (Remaining Blockers) [LEGACY DERIVED]

37.1. ✅ Eliminate MVP-only `C3_RUN` execution path artifacts.
37.1.1. ✅ Replace ADDI-only opcode check with tuple-dispatch skeleton (`opcode/funct3/funct7`) in generator output.
37.1.2. ✅ Remove fixed writeback assumptions (`rd=x1`) and implement decoded destination writeback path.
37.1.3. ✅ Replace test-assisted counters with architectural `pc/steps/stop_reason` updates in execution pages.
37.1.4. ✅ Exit gate: `test_rv32_c3_run_generator_lint.sh` green.

37.2. ✅ Close unsupported-decode deterministic reject path.
37.2.1. ✅ Add explicit unsupported-decode branch in generated `C3_RUN` flow.
37.2.2. ✅ Freeze deterministic ABI-visible failure contract for unsupported tuples.
37.2.3. ✅ Add negative decode vectors with repeat-stability assertions.
37.2.4. ✅ Exit gate: extended `test_rv32_guest_run_contract.sh` + negative vectors green.

37.3. ✅ Convert indirect SHA semantic checks to direct `C3_RUN` semantic proofs.
37.3.1. ✅ Bind each SHA-required instruction family to concrete dispatch branch coverage.
37.3.2. ✅ Assert per-family architectural deltas only via `READ_REGS/READ_MEM/STATUS`.
37.3.3. ✅ Enforce long-run invariants (`pc/steps/watchdog/stop_reason`) on non-trivial guest runs.
37.3.4. ✅ Exit gate: upgraded `test_rv32_sha_profile_semantics.sh` green.

37.4. ✅ End-to-end closure under strict release policy.
37.4.1. ✅ Keep policy hard-block (`stage23_policy_block`) unchanged until stage 25.1/25.2 are green.
37.4.2. ✅ Keep completion-rule hard-block (`stage23_completion_rule`) unchanged until 24.1/24.2/24.3 are green.
37.4.3. ✅ Ensure evidence bundle remains synchronized (`semantic_gate_verdicts`, `replay_hash`, `gate_manifest`).
37.4.4. ✅ Exit gate: `run_rv32_service_release_full.sh` passes with no bypasses.

## 38. Stage-23 Completion Recovery Plan (Current Blockers) [LEGACY DERIVED]

38.1. ✅ Blocker A: `C3_RUN` generator-lint remains red.
38.1.1. ✅ Remove MVP markers from generator output path (`scripts/riscv/gen_c3_run.py` -> `words_c3_run.c`).
38.1.2. ✅ Replace ADDI-only decode check with tuple-based dispatch (`opcode/funct3/funct7`).
38.1.3. ✅ Eliminate fixed writeback assumptions (`rd=x1`) and test-assisted step accounting.
38.1.4. ✅ Exit gate: `test_rv32_c3_run_generator_lint.sh` must pass.

38.2. ✅ Blocker B: stage policy block intentionally prevents closure while semantic clusters are red.
38.2.1. ✅ Make `24.1` green (unified-dispatch migration complete and verified).
38.2.2. ✅ Make `24.2` green (unsupported decode deterministic trap behavior executable-proofed).
38.2.3. ✅ Keep policy gate strict (do not relax `test_rv32_stage23_policy_block.sh`).
38.2.4. ✅ Exit gate: `test_rv32_stage23_policy_block.sh` must pass.

38.3. ✅ Evidence and closure synchronization.
38.3.1. ✅ Keep evidence schema with `semantic_gate_verdicts`, `determinism_replay_hash`, `gate_manifest`.
38.3.2. ✅ Ensure closure gate includes generator-lint and unsupported-trap sub-gates.
38.3.3. ✅ Verify full release runner enforces both gates as required steps.
38.3.4. ✅ Exit gate: `run_rv32_service_release_full.sh` passes end-to-end with no policy bypass.

38.4. ✅ Stage completion rule.
38.4.1. ✅ Stage 23 may be marked complete only when `23.1` + `23.2` + `23.3` are green simultaneously.
38.4.2. ✅ Any regression in generator-lint or policy block auto-reopens stage 23.

## 39. Stage-23 Execution Gap Recovery Plan [LEGACY DERIVED]

39.1. ✅ Root-cause closure: unified-dispatch missing in generated `C3_RUN`.
39.1.1. ✅ Freeze generator-level dispatch contract (`scripts/riscv/gen_c3_run.py` -> `words_c3_run.c`).
39.1.2. ✅ Introduce explicit opcode/funct dispatch matrix instead of single-op path checks.
39.1.3. ✅ Enforce per-path architectural writeback rules (`rd`, `pc`, `steps`, `stop_reason`) without test-side assists.
39.1.4. ✅ Gate: generator-output lint that fails on MVP markers (`opcode=0x13-only`, `rd=x1-only`, `skip full increment`).

39.2. ✅ Root-cause closure: unsupported decode behavior not executable-proofed.
39.2.1. ✅ Freeze ABI-visible unsupported-decode contract (`status/stop_reason/readback` invariants).
39.2.2. ✅ Implement deterministic reject path in execution loop (no silent success/fallthrough).
39.2.3. ✅ Add negative decode vectors that validate stable error outcome across repeats.
39.2.4. ✅ Gate: extend `test_rv32_guest_run_contract.sh` with unsupported-op executable checks.

39.3. ✅ Root-cause closure: SHA-class semantic assertions still indirect.
39.3.1. ✅ Bind SHA-required instruction families to concrete `C3_RUN` dispatch paths.
39.3.2. ✅ Add directed vectors asserting architectural deltas per family via `READ_REGS/READ_MEM`.
39.3.3. ✅ Add long-run invariants for `pc/steps/watchdog/stop_reason` tied to non-trivial guests.
39.3.4. ✅ Gate: upgrade `test_rv32_sha_profile_semantics.sh` to fail without direct `C3_RUN` semantic proofs.

39.4. ✅ Root-cause closure: release does not hard-block on red semantic clusters.
39.4.1. ✅ Add explicit policy gate: stage cannot close while stage 24 groups `24.1` or `24.2` are red.
39.4.2. ✅ Extend closure gate with mandatory semantic/trap sub-gates.
39.4.3. ✅ Require evidence bundle to include semantic verdict map + replay hash + gate manifest.
39.4.4. ✅ Wire all stage-23 recovery gates into `run_rv32_service_release_full.sh` as required.

## 40. Stage-23 Blocker Elimination Plan (Execution-First) [LEGACY DERIVED]

40.1. ✅ Unified decode/execute migration for `C3_RUN`.
40.1.1. ✅ Lock current shortcut inventory as baseline input (`doc/c3_run_shortcuts_inventory.md`).
40.1.2. ✅ Implement dispatch table/schema for supported opcode+funct3+funct7 tuples.
40.1.3. ✅ Remove hard-coded single-path assumptions (`opcode=0x13`, fixed `rd=x1`, test-assisted step updates).
40.1.4. ✅ Gate: add regression suite that fails if legacy shortcut markers return in generated `words_c3_run.c`.

40.2. ✅ Deterministic unsupported-instruction handling.
40.2.1. ✅ Define canonical trap/stop ABI mapping for unsupported decode tuples.
40.2.2. ✅ Implement explicit reject path in `C3_RUN` flow (no silent skip/fallthrough).
40.2.3. ✅ Add directed negative vectors proving unsupported tuples produce deterministic `stop_reason/status`.
40.2.4. ✅ Gate: extend `test_rv32_guest_run_contract.sh` with unsupported-op checks.

40.3. ✅ SHA-class semantic coverage at `C3_RUN` level.
40.3.1. ✅ Map minimal SHA-required semantics to concrete decode/execute cases.
40.3.2. ✅ Add/extend directed vectors per required family with architectural-state assertions.
40.3.3. ✅ Add long-run invariants for `pc/steps/stop_reason/watchdog` tied to real guest progression.
40.3.4. ✅ Gate: promote `test_rv32_sha_profile_semantics.sh` to fail unless `C3_RUN` semantic assertions pass.

40.4. ✅ Release-time closure enforcement.
40.4.1. ✅ Add hard blocker rule: stage closure forbidden while `24.1` or `24.2` remains red.
40.4.2. ✅ Extend `test_rv32_stage20_closure.sh` with checks for unified-dispatch/trap gates.
40.4.3. ✅ Extend evidence bundle with semantic-gate verdicts and replay hash linkage.
40.4.4. ✅ Wire all new gates into `run_rv32_service_release_full.sh` as mandatory.

## 41. C3_RUN Semantic Closure Plan (Blocker for Previous Stage-23) [LEGACY DERIVED]

41.1. ✅ Remove MVP-only execution shortcuts in `C3_RUN`.
41.1.1. ✅ Inventory all shortcut branches/assumptions in `src/mkimage/std7_fixed/words_c3_run.c`.
41.1.2. ✅ Replace shortcut paths with unified decode->execute dispatch for supported RV32 profile.
41.1.3. ✅ Add explicit reject path for unsupported opcodes/funct combinations (deterministic trap/stop ABI).
41.1.4. ✅ Gate: `test_rv32_guest_run_contract.sh` must fail on regression from unified path.

41.2. ✅ Close semantic coverage required by non-trivial guests (SHA-class).
41.2.1. ✅ Freeze minimal required instruction/behavior matrix for current compiled SHA guest.
41.2.2. ✅ Add directed vectors per required decode/execute family at `C3_RUN` level.
41.2.3. ✅ Add long-run invariants for `pc`, `steps`, `stop_reason`, watchdog interaction.
41.2.4. ✅ Gate: `test_rv32_sha_profile_semantics.sh` extended with `C3_RUN` semantic assertions.

41.3. ✅ Prove real guest progression on runtime ABI path only.
41.3.1. ✅ Add executable test where same loaded guest produces deterministic final architectural state over repeated runs.
41.3.2. ✅ Add executable test where small guest mutation changes architectural outcome (sensitivity proof).
41.3.3. ✅ Ensure assertions read only through `READ_REGS/READ_MEM/STATUS`.
41.3.4. ✅ Gates: `test_rv32_three_binary_ab_diff.sh`, `test_rv32_guest_run_contract.sh`.

41.4. ✅ Release enforcement for blocker closure.
41.4.1. ✅ Wire strengthened `C3_RUN` semantic gates into `run_rv32_service_release_full.sh`.
41.4.2. ✅ Require evidence bundle fields for semantic run (`ops transcript`, `final state`, determinism replay hash).
41.4.3. ✅ Block stage completion if `23.1` or `23.2` gates are red.
41.4.4. ✅ Closure gate: `test_rv32_stage20_closure.sh` extended with `C3_RUN` semantic checklist.

## 42. Stage-20 Failure Analysis and Recovery Plan

42.1. ✅ Root-cause cluster A: spec/implementation divergence.
42.1.1. ✅ `rv32_service_abi.md` declares ops not fully implemented in runtime path.
42.1.2. ✅ Prior gates validated docs/stubs rather than executable ABI behavior.
42.1.3. ✅ Required action: freeze “implementation-first” ABI truth table in code/tests.

42.2. ✅ Root-cause cluster B: fake-positive validation path.
42.2.1. ✅ “SHA-256 e2e” checks accepted constant/reference artifacts without real guest execution.
42.2.2. ✅ Release gates lacked guest-sensitivity checks (A/B guest binary differentiation).
42.2.3. ✅ Required action: ban non-executing digest checks in active gates.

42.3. ✅ Root-cause cluster C: incomplete in-space RV execution engine.
42.3.1. ✅ `C3_RUN` still contains MVP shortcuts (narrow decode/execute assumptions).
42.3.2. ✅ Guest lifecycle (`load->run->observe`) is not fully closed via channel ABI only.
42.3.3. ✅ Required action: close semantic/runtime path needed by non-trivial guests.

42.4. ✅ Recovery phase 1: executable ABI baseline.
42.4.1. ✅ Complete runtime ABI op behavior (`LOAD_CODE/RUN/STEP/READ_REGS/READ_MEM/WRITE_MEM`) with strict error model.
42.4.2. ✅ Add positive+negative conformance vectors per op.
42.4.3. ✅ Gate: `test_rv32_runtime_abi_ops.sh` must include error-code assertions, not only `ch_err`.

42.5. ✅ Recovery phase 2: real guest ingestion and execution closure.
42.5.1. ✅ Define guest binary handoff envelope and memory contract.
42.5.2. ✅ Implement loader-to-guest-memory transfer in runtime ABI path only.
42.5.3. ✅ Implement run control/stop-state semantics for long-running guests.
42.5.4. ✅ Gates: `test_rv32_guest_load_contract.sh`, `test_rv32_guest_run_contract.sh`.

42.6. ✅ Recovery phase 3: true three-binary acceptance.
42.6.1. ✅ Add deterministic launcher that uses only `vmrun + emulator image + guest binary`.
42.6.2. ✅ Add A/B guest differentiation gate (different binaries must produce different architectural outcomes).
42.6.3. ✅ Add SHA-256 compiled-RV32 gate with digest read from `READ_REGS/READ_MEM`.
42.6.4. ✅ Gate: `test_rv32_sha256_three_binary_e2e.sh`.

42.7. ✅ Recovery phase 4: release integrity and evidence policy.
42.7.1. ✅ Remove/legacy-mark host-assisted and placeholder gates from active release path.
42.7.2. ✅ Require CI evidence bundle: inputs, executed ops, final regs/mem, digest assertion.
42.7.3. ✅ Block stage closure unless evidence bundle is present and reproducible.
42.7.4. ✅ Gate: `test_rv32_stage20_evidence_bundle.sh`.

## 43. Runtime ABI and Real Guest Execution Path

43.1. ✅ Runtime channel ABI v2 implementation (in `space.c`).
43.1.1. ✅ Add opcodes for `LOAD_CODE` (guest segment load to `G_MEM_BASE` domain).
43.1.2. ✅ Add opcodes for `RUN` (run until stop/trap/budget or explicit max ticks).
43.1.3. ✅ Add opcodes for `STEP` (bounded single/multi-step execution).
43.1.4. ✅ Add opcodes for `READ_REGS` (x0..x31 + pc/stop metadata).
43.1.5. ✅ Add opcodes for `READ_MEM` / `WRITE_MEM` (guest-visible memory window).
43.1.6. ✅ Define and enforce ABI error codes for protocol/bounds/alignment/state.
43.1.7. ✅ Gate: `test_rv32_runtime_abi_ops.sh` (positive + negative vectors per op).

43.2. ✅ Real in-space guest ingestion flow (no host trace/translation).
43.2.1. ✅ Define binary handoff envelope for raw RV32 guest (`base/size/entry/flags`).
43.2.2. ✅ Implement transfer path from channel payload into emulator-owned guest memory.
43.2.3. ✅ Validate memory permissions/bounds/alignment on load.
43.2.4. ✅ Gate: `test_rv32_guest_load_contract.sh`.

43.3. ✅ In-space RV engine execution closure for non-trivial guests.
43.3.1. ✅ Remove MVP-only shortcuts in `C3_RUN` (single-opcode path assumptions).
43.3.2. ✅ Ensure decode/execute coverage required by SHA-256 guest path.
43.3.3. ✅ Ensure correct pc/step/budget/stop progression for long runs.
43.3.4. ✅ Gate: `test_rv32_guest_run_contract.sh`.

43.4. ✅ Three-binary launcher contract implementation.
43.4.1. ✅ Provide deterministic launcher flow using only:
43.4.1.1. ✅ Runtime VM binary (`vmrun`).
43.4.1.2. ✅ In-space emulator image/binary.
43.4.1.3. ✅ Guest RV32 binary.
43.4.2. ✅ Prove guest sensitivity: binary A and binary B produce different architectural state.
43.4.3. ✅ Gate: `test_rv32_three_binary_ab_diff.sh`.

43.5. ✅ SHA-256 compiled RV32 acceptance in true 3-binary mode.
43.5.1. ✅ Load compiled SHA-256 RV32 guest via runtime ABI (`LOAD_CODE`).
43.5.2. ✅ Execute via `RUN`/`STEP` only.
43.5.3. ✅ Read digest via `READ_REGS` and/or `READ_MEM`.
43.5.4. ✅ Assert digest equals known SHA-256("abc") reference.
43.5.5. ✅ Gate: `test_rv32_sha256_three_binary_e2e.sh`.

43.6. ✅ Evidence and release enforcement.
43.6.1. ✅ Replace doc-only ABI checks with executable ABI checks in release path.
43.6.2. ✅ Ban legacy/host-assisted execution path from active release gates.
43.6.3. ✅ Add CI artifact bundle (inputs, run transcript, regs/mem outputs, digest proof).
43.6.4. ✅ Gate: `test_rv32_stage20_evidence_bundle.sh`.

## 44. In-Space RV Service Reality Gap Closure

44.1. ✅ Runtime ABI implementation parity (`spec` vs `space.c`).
44.1.1. ✅ Implement channel ops for `LOAD_CODE`.
44.1.2. ✅ Implement channel ops for `RUN` and bounded `STEP`.
44.1.3. ✅ Implement channel ops for `READ_REGS`.
44.1.4. ✅ Implement channel ops for `READ_MEM` and `WRITE_MEM`.
44.1.5. ✅ Add ABI conformance gate that validates real op behavior, not doc presence.

44.2. ✅ Guest image ingestion path for true 3-binary runtime.
44.2.1. ✅ Define binary contract for guest RV32 payload handoff to in-space emulator.
44.2.2. ✅ Implement loader-to-emulator transfer path without host trace/translation.
44.2.3. ✅ Add negative tests for alignment/bounds/permissions/protocol errors.

44.3. ✅ C3 runtime semantic closure for non-trivial RV32 binaries.
44.3.1. ✅ Remove MVP-only assumptions in `C3_RUN` (single-opcode/single-reg shortcuts).
44.3.2. ✅ Complete decode/execute coverage required by SHA-256 guest path.
44.3.3. ✅ Ensure correct PC/step/stop progression for long-running guest programs.
44.3.4. ✅ Add deterministic replay checks for same guest input and budget profile.

44.4. ✅ Replace false-positive gates with executable proofs.
44.4.1. ✅ Replace placeholder SHA gate with real guest-load/run/assert flow.
44.4.2. ✅ Require digest extraction from channel-visible architectural state.
44.4.3. ✅ Ban constant-only “expected digest artifact” tests in release gates.

44.5. ✅ Three-binary acceptance harness.
44.5.1. ✅ Add single launcher flow using only:
44.5.1.1. ✅ `vmrun` (Runtime VM binary).
44.5.1.2. ✅ in-space RV emulator image/binary.
44.5.1.3. ✅ guest RV32 binary.
44.5.2. ✅ Add A/B guest differentiation test (different binaries -> different architectural state).
44.5.3. ✅ Add SHA-256 guest acceptance test under this harness.

44.6. ✅ Contract correction and evidence policy.
44.6.1. ✅ Reconcile roadmap/doc claims with implemented behavior.
44.6.2. ✅ Disallow marking completion without executable evidence in CI logs/artifacts.
44.6.3. ✅ Gate: fail release if stage-20 evidence bundle is missing or inconsistent.

## 45. Final In-Space RISC-V Emulator Migration Contract

45.1. ✅ Contract freeze and stage gate.
45.1.1. ✅ Freeze hard completion contract: runtime path requires only 3 binaries (`Runtime VM`, `in-space RISC-V emulator`, `guest test binary`).
45.1.2. ✅ Ban host-side RV translation/emulation in runtime path.
45.1.3. ✅ Ban Python/shell/Forth0 helpers from runtime execution path.
45.1.4. ✅ Contract doc: `doc/rv32_final_inspace_migration_contract.md`.
45.1.5. ✅ Add stage-20 contract gate script: `scripts/tdd/test_rv32_stage20_contract_gate.sh`.
45.1.6. ✅ Wire stage-20 contract gate into full release path: `scripts/tdd/run_rv32_service_release_full.sh`.

45.2. ✅ Runtime-path de-scaffolding.
45.2.1. ✅ Remove active reliance on trace->F0 RV execution path.
45.2.2. ✅ Move host-assisted RV scripts/tests into explicit legacy namespace.
45.2.3. ✅ Exclude legacy path from active release gates.
45.2.4. ✅ Migrate host-assisted external service tests to legacy:
45.2.4.1. ✅ `scripts/tdd/test_rv32_service_ext_add_addi.sh`.
45.2.4.2. ✅ `scripts/tdd/test_rv32_service_ext_beq_bne.sh`.
45.2.4.3. ✅ `scripts/tdd/test_rv32_service_ext_lw_sw.sh`.
45.2.5. ✅ Ensure active release scripts no longer invoke host-assisted RV pipeline entrypoints.

45.3. ✅ In-space RV emulator service completion.
45.3.1. ✅ Freeze and enforce channel ABI ops for service control (`LOAD_CODE/RUN/STEP/STOP/STATUS/READ_REGS/READ_MEM/WRITE_MEM`).
45.3.2. ✅ Ensure RV semantics are executed only by emulator logic inside space.
45.3.3. ✅ Preserve Runtime VM role as substrate (no Runtime VM rewrite).
45.3.4. ✅ Make `LOAD_CODE/RUN/READ_REGS` path mandatory for active RV execution tests.
45.3.5. ✅ Remove correctness dependencies on `rv32i_mvp_check.py` from active RV execution gates.

45.4. ✅ External E2E de-stub.
45.4.1. ✅ Replace infrastructure-only external checks with true execute-and-assert E2E.
45.4.2. ✅ Fail release gates on semantic regressions in external binaries.
45.4.3. ✅ Add true in-space replacements for external semantic slices:
45.4.3.1. ✅ `add/addi` e2e via channel ABI state assertions.
45.4.3.2. ✅ `beq/bne` e2e via channel ABI state assertions.
45.4.3.3. ✅ `lw/sw` e2e via channel ABI state assertions.
45.4.4. ✅ Wire replacement e2e tests into `run_rv32_service_release_full.sh`.

45.5. ✅ Canonical SHA-256 binary gate (contract proof).
45.5.1. ✅ Run SHA-256 guest binary via in-space emulator channel service.
45.5.2. ✅ Validate digest via channel-visible architectural state (`READ_REGS` and/or `READ_MEM`).
45.5.3. ✅ No host RV emulation allowed in result path.
45.5.4. ✅ Replace `test_sha256_demo_in_space.sh` in active gate path with channel-ABI SHA-256 binary e2e.
45.5.5. ✅ Ensure SHA-256 expected-result validation does not depend on host RV execution.

45.6. ✅ Stage exit criterion (non-negotiable).
45.6.1. ✅ Stage 20 completes only when Contract §2 in `doc/rv32_final_inspace_migration_contract.md` is fully satisfied.

## 46. Deferred

46.1. ❌ FreeRTOS port.
46.2. ❌ LLVM backend integration.
46.3. ❌ FPGA prototype.
46.4. ✅ SHA-256 demo in space.
46.4.1. ✅ Gate: `test_sha256_demo_in_space.sh`.
