# RV32I MVP Contract (Narrow C2 Scope)

Status date: 2026-05-31
Owner: riscv-port C2 pipeline

## 1) Goal
Run a narrow RV32I subset through Copy-Space C2 pipeline (`trace -> .f0 -> .tok -> VM`) with deterministic, reproducible verification against Python reference execution.

## 2) Non-goals
- No RV32M/A/F/D/C
- No CSR, interrupts, exceptions, virtual memory, syscalls
- No generic ELF runtime

## 3) Fixed Scope
- Input: small raw machine-code binaries
- Memory model: fixed flat memory mapping
- Deterministic stop condition: max instruction budget + VM life budget

## 4) Acceptance Gates
All gates must pass for MVP completion:
1. Functional: all tests in the MVP set pass reference-vs-trace checks.
2. Stability: no nondeterministic failures over 3 repeated runs.
3. Pipeline: `riscv_trace_to_f0.py` CLI and `run_riscv_f0.sh` demo path work end-to-end.
4. Diagnostics: failing runs produce actionable trace/log artifacts.

## 5) Metrics Budget (initial, adjustable by evidence)
- Max traced instructions per MVP program: 256
- Max `.f0` lines per MVP program: 20,000
- Max `.tok` bytes for MVP runs: 1,500,000
- Max VM compile ticks (observed): 20,000,000
- Max VM run ticks (observed): 20,000,000

Notes:
- These are initial engineering guardrails, not hard architecture limits.
- Budgets may be tightened/relaxed after stable baseline measurements.

## 6) MVP Test Set (v1)
- T0: demo arithmetic/store (`addi`, `add`, `sw`)
- T1: branch taken (`beq`)
- T2: branch taken (`bne`)
- T3: shift path (`sll`, `srl`)
- T4: store/load roundtrip (`sw`, `lw`)

## 7) Current Risks
1. Trace expansion inflates `.tok` and may fail compile-stage VM bounds.
2. `riscv_to_f0.py` coverage/semantics mismatch for some RV32I forms.
3. Incomplete parity checks between Python execution and generated trace behavior.

## 8) Next Implementation Steps
1. Land CLI + artifact emission in `riscv_trace_to_f0.py`.
2. Add MVP harness script to emit trace/f0 stats and basic consistency checks.
3. Add TDD smoke test for the new CLI-driven demo path.
4. Incrementally expand checks from trace-level to VM-level where deterministic expectations exist.

## 9) Implementation Status (2026-05-31)
Completed:
1. `riscv_trace_to_f0.py` CLI is implemented (`--binary`, `--out`, `--trace-json`, `--max-instr`, `--entry-point`, `--reg-init`).
2. Trace artifacts now include per-step fields: `pc_after`, `rd_value`, `mem_write`.
3. `scripts/riscv/rv32i_step_diff.py` implemented: replay-based step consistency checker.
4. `scripts/riscv/rv32i_mvp_check.py` integrated with step-diff + trace digest.
5. Staged runner `scripts/riscv/run_staged_plan.sh` implemented with Wave A-E cases and:
   - instruction requirements,
   - `.tok` size budget gate,
   - compile/run tick budget gates,
   - repeatability gate (`REPEAT_RUNS`, default 3) via stable `trace_sha256`.
6. TDD integration complete:
   - `scripts/tdd/test_rv32i_mvp_trace.sh`
   - `scripts/tdd/test_rv32i_staged_plan.sh`
   - `scripts/tdd/test_rv32i_emitter_contract.sh`
   - all wired into `scripts/tdd/run_all.sh`.

Remaining before full MVP closure:
1. Add stronger VM-level equivalence checks (beyond trace replay consistency).
2. Deepen semantic checks for load/store + jump instructions against full VM traces.

## 10) Contracts and Gates
1. Emitter contract is documented in `doc/riscv_emitter_contract.md`.
2. `scripts/tdd/test_rv32i_emitter_contract.sh` enforces no `UNSUPPORTED` in staged Wave A-E outputs.
3. `scripts/riscv/run_staged_plan.sh` enforces `.tok` size + tick budgets + repeatability.
