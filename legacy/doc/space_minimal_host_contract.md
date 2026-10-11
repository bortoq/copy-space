# Space Minimal Host Contract

The host-side emulator wrapper is kept minimal. Its job is to:

1. Load a full image into `vm->space`.
2. Run ticks for a bounded `life`.
3. Optionally dump the final `vm->space`.

It does not own guest semantics.
It does not interpret RISC-V.
It does not implement resident request/response behavior.
All resident execution and resident channel semantics live in `src/vm/space.c`.

This document is the host-side counterpart of the resident `space.c` contract.
