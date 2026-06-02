# C3 Trace Schema v1

Status: active for S8 (Observability Hardening).

## Modes

- `full`: debug-oriented payload, includes execution mode.
- `compact`: CI-oriented payload with reduced fields.

## Common contract

Trace is a JSON array of step objects ordered by `step` ascending.

Required fields in both modes:
- `step` (int)
- `guest_pc` (int)
- `instr_name` (string)
- `rd` (int|null)
- `rd_value` (int|null)
- `mem_write` (object|null)
- `stop_reason` (int|null)

`mem_write` object shape (when non-null):
- `addr` (int)
- `size` (int)
- `value` (int)

## Full mode

Additional required field:
- `mode` (string): `native|scaffold`

## Compact mode

- Field `mode` is omitted by contract.

## Repro bundle (first mismatch)

`c3_run_and_diff.sh` writes:
- `c3_trace.json`
- `ref_trace.json`
- `diff.stdout.log`
- `diff.stderr.log`
- `diff.txt` (copy of stderr on mismatch)
- `meta.json`
- `stop_dump.bin` (placeholder until native stop-dump wiring)
- optional runtime artifact directory `runtime/` for native cases
