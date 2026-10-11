# RV32 C3 Dispatch Contract (Stage-23)

Status: frozen baseline (generator-level contract).

## Producer/consumer chain
- Source of truth for C3 dispatch generation: `scripts/riscv/gen_c3_run.py`.
- Generated artifact consumed by runtime image builder: `src/mkimage/std7_fixed/words_c3_run.c`.
- Contract requires deterministic generation for identical generator input.

## Dispatch expectations
- Dispatch must be explicit over decode tuple dimensions:
  - `opcode`
  - `funct3`
  - `funct7` (where applicable)
- Unsupported tuples must route to deterministic reject/trap path (no silent success).

## Invariant policy
- Generator and committed generated output must be in sync.
- MVP-only shortcuts are forbidden for completion state:
  - single-opcode-only execution path,
  - fixed destination register assumptions,
  - test-assisted accounting in place of architectural accounting.
