# RV32I Emitter Contract (C2 Trace Mode)

Status date: 2026-05-31
Scope: `riscv-port/riscv_to_f0.py` used by trace-driven C2 pipeline.

## Model
- This contract is for **trace mode**: control-flow is already resolved by Python emulator.
- Branch/jump emitters are metadata no-ops in `.f0` (comments), because only executed path is emitted.

## Per-instruction Contract
| Instruction class | Required effect |
|---|---|
| `add/sub/addi/xor/or/and/andi/ori/xori` | Update `rd` with 32-bit wrapped result |
| `sll/srl/sra` + `slli/srli/srai` | Apply shift with RV32I shift-mask semantics (`& 0x1f`) |
| `slt/sltu/slti/sltiu` | Write `rd` = 0/1 according to signed/unsigned compare |
| `lui/auipc` | `lui`: set immediate upper bits; `auipc`: trace-resolved marker accepted |
| `lb/lbu/lh/lhu/lw` | Load size/sign behavior represented in emitted operations |
| `sb/sh/sw` | Store selected width from `rs2` |
| `beq/bne/blt/bge/bltu/bgeu/jal/jalr` | Must be recognized; trace-mode emitter may be no-op/comment |

## Gating Rules
1. No `UNSUPPORTED` lines in generated `.f0` for MVP waves A-E cases.
2. `rv32i_mvp_check.py` + `rv32i_step_diff.py` must pass for each wave case.
3. Staged budgets (`tok_bytes`, `compile_ticks`, `run_ticks`) must pass.
