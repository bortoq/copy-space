# Minimal Path — Single-Goal Mode

Goal: demonstrate non-trivial computation running inside Copy-Space address space.

## Priority Order
1. Copy-Space VM core correctness/stability.
2. RISC-V C2 path (`trace -> .f0 -> .tok -> VM`) and RV32I MVP completion.
3. Demonstration workloads proving meaningful computation in-space.

Everything else is secondary and may be deferred.

## Critical Directories
- `src/vm/**`
- `src/tools/vmrun.c`, `src/tools/vmprep_forth0.c`
- `src/forth0/**` (only as needed for C2 pipeline)
- `riscv-port/**`
- `scripts/riscv/**`
- `scripts/forth0/run_f0.sh`
- `scripts/tdd/test_rv32i_*.sh`
- `scripts/tdd/test_vmrun_trace_jsonl.sh`

## Deferred Tracks
- Scheduler v0 productization and bench polishing
- LLVM backend integration
- FreeRTOS port
- FPGA prototype
- SHA-256 demo in space (until RV32I MVP is closed)

## Required Gates (Single-Goal)
Use this command as the default quality gate:

```bash
scripts/tdd/run_rv32i_minimal.sh
```

This gate must pass before claiming RV32I MVP progress.

## Success Definition
- Wave A-E staged checks pass with deterministic repeatability.
- Step-diff gates pass.
- Size/tick budgets pass.
- At least one non-trivial computation demo runs in-space end-to-end.
