# C3 Stop/Error Contract (M0)

Status date: 2026-05-31
Scope: initial executable contract for native in-space RV32I interpreter track (C3).

## C3 State Layout (S1, v1 freeze)
All values below are bit-addresses in VM space (24-bit for current profile).

- `C3_LAYOUT_VER = 1`
- `G_PC = 0x001000`
- `G_STEP_BUDGET = 0x001020`
- `G_STEPS = 0x001040`
- `G_REG_BASE = 0x001200`
- `G_MEM_BASE = 0x002000`
- `G_STOP_REASON = 0x001080`

Layout invariants:
- `G_STEP_BUDGET - G_PC = 0x20` bits
- `G_STEPS - G_STEP_BUDGET = 0x20` bits
- stop/error block remains defined by TESTG dump contract below

## Stop Reasons
- `1`: guest HALT reached
- `2`: guest step budget exhausted
- `3`: illegal instruction
- `4`: memory fault (alignment/bounds)
- `5`: arithmetic fault (RV32M trap-class: e.g., configured trap-on-arithmetic path)

## Memory Policy (Pre-S5 Freeze)
- Alignment policy: `trap` (unaligned accesses are faults).
- Fault reporting:
  - `reason = 4`
  - `fault_addr` contains offending guest address (u32).
- Scope for S5: `sw/lw` only (subword ops are out of S5 scope).

## TESTG State Dump Layout
All values are byte-addressed in TESTG and encoded big-endian for u32 fields.

- Byte `0`: `reason` (`u8`)
- Bytes `1..4`: `guest_pc` (`u32`)
- Bytes `5..8`: `instr` (`u32`)
- Bytes `9..12`: `fault_addr` (`u32`)
- Bytes `13..16`: `guest_steps` (`u32`)
- Bytes `17..19`: reserved (`0`)

## M0 Guarantees
- Any C3 stop path must write this state block before VM halt.
- `reason` is always non-zero on stop.
- `guest_pc` always points to the instruction being reported.
- `reserved[17..19]` are always zero.

## M0 Validation
- `src/forth0/tests/test_c3_m0_stop_contract.f0`
- `scripts/tdd/test_c3_m0_stop_contract.sh`
- `scripts/riscv/c3_trace_diff.py`
- `scripts/tdd/test_c3_trace_diff.sh`
- `src/forth0/tests/test_c3_layout.f0`
- `scripts/tdd/test_c3_layout.sh`
