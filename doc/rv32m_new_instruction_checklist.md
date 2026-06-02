# RV32M New Instruction Checklist

Use this checklist for each new RV32M instruction (or tightly coupled pair).

1. Contract
- Add or update exact semantics in `doc/rv32m_m_semantics_contract.md`.
- Document corner-cases explicitly.

2. Vectors
- Add directed cases in `scripts/riscv/rv32m_semantics_vectors.py`.
- Ensure case covers sign/zero behavior and boundary values.

3. Truth Gate
- `sh scripts/tdd/test_rv32m_m_semantics_vectors.sh` must pass.

4. Runtime Implementation
- Implement instruction path in C3 runtime with stop/error ABI preserved.

5. Diff Gate
- Add or update differential gate vs reference trace.
- Mismatch must produce repro bundle.

6. Budget Gate
- Add/extend M-slice budget checks (`tok/compile/run/ticks_per_1k`).

7. Preflight
- `sh scripts/tdd/run_rv32m_preflight.sh` must pass.

8. Regression
- `sh scripts/tdd/run_c3_staged.sh` and `sh scripts/tdd/run_rv32i_minimal.sh` must pass.
