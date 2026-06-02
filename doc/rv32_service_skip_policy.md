# RV32 Service Skip/Waiver Policy

Scope: strict black-box external corpus gate (zero-waiver mode).

Rules:
- Local vendored corpus only (`third_party/riscv-external`).
- VM-level execution is required.
- `allowed_failures` is empty in strict mode.
- Any failure fails the gate.
