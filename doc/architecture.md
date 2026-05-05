# Architecture (very short)

## Memory model
- There is one memory array called `space`.
- Addressing is in bits (bit-addressable).

## Instruction model
Each instruction slot is a copy:

    copy(n, dst, src)

Meaning:
- copy `n` bits from `src` to `dst` inside `space`.

A VM tick executes a fixed number of instruction slots.

## Determinism
Given the same initial image and the same input, the result is deterministic.
External I/O is modeled explicitly (MMIO handshake), so it can be tested and validated.

