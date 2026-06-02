# C2 Legacy Reference Policy

Status: active from 2026-06-01.

## Role

C2 (`trace -> .f0 -> .tok -> VM`) is no longer the primary runtime path.
It is maintained as a legacy-reference and diagnostic oracle for C3.

## Gate policy

- Primary release gate: `scripts/tdd/run_c3_staged.sh`
- Secondary safety gate: `scripts/tdd/run_rv32i_minimal.sh`

## Scope policy

Allowed in C2:
- bugfixes
- diagnostics improvements
- regression-oracle maintenance

Not allowed in C2 (without explicit decision):
- new feature track
- widening ISA scope as primary execution path

## Exit options

After stable C3 cycles, choose one:
1. Keep C2 as oracle-only long-term.
2. Archive C2 to maintenance/legacy area.
