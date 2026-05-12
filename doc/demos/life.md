# Demo: Conway's Game of Life on VM/Forth0

File: doc/demos/life.md

This is a small, deterministic demo program for the VM/Forth0 toolchain.
It is intended as a geek-friendly under-the-hood example, not as part of the scheduler v0 product path.

Source
- Forth0 demo: src/forth0/demos/life.f0

------------------------------------------------------------

## What it does

- Uses a small padded grid (8x8 bits, 1 byte per row).
- Initializes a classic blinker pattern in GEN0 (horizontal, three live cells).
- Computes GEN1 for the 3x3 region around the blinker center.
- Writes both generations into TESTG and halts.

Why the scope is intentionally small
- In this toolchain, compile-time loops expand into token streams.
- A full-grid implementation can generate a very large token stream and slow down the VM compile phase.
- This demo is kept minimal to stay fast and deterministic.

------------------------------------------------------------

## How to run

Build the native tools first:

  make bins

Run the demo and verify the expected TESTG dump:

  scripts/forth0/run_f0.sh --in src/forth0/demos/life.f0 --dump-testg 16 --expect-hex 00000038000000000000101010000000

If you want to inspect artifacts (compiled image, after image, stderr logs), add --keep:

  scripts/forth0/run_f0.sh --in src/forth0/demos/life.f0 --dump-testg 16 --keep

------------------------------------------------------------

## Output layout (TESTG dump)

The first 16 bytes of TESTG are:

- bytes 0..7: GEN0 (8 rows)
- bytes 8..15: GEN1 (8 rows)

Each byte encodes one row. Bit addressing follows the existing Forth0 tests:
- bit 0 corresponds to 0x80
- bit 7 corresponds to 0x01

For this demo:
- GEN0 has 0x38 at row 3 (cols 2..4 live), all other rows are 0x00
- GEN1 has 0x10 at rows 2, 3, 4 (a vertical blinker at col 3), all other rows are 0x00

Expected 16-byte hex dump:

  00000038000000000000101010000000

------------------------------------------------------------

## Scope note

This demo is separate from the scheduler v0 interfaces.
Stable, partner-facing surfaces are documented in doc/audit_v0.md and doc/audit_report_v0.md.
