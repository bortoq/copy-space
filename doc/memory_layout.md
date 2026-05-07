# Memory layout / regions (std7_fixed)

_file: doc/memory_layout.md_

This document explains how `space` is typically partitioned into regions, and what `.f0` programs/tests are allowed to touch.

The VM memory is **bit-addressable**:
- addresses are **bitaddrs** (bit offsets into `space`)
- byte offset is: `byte = bitaddr / 8`

---

## High-level regions

At runtime the VM has several logical regions. Some are internal (do not touch from user programs),
some are explicitly published via ART and intended for use.

### Processor region (internal)
Contains the per-tick slot array (the “processor” / slot memory).

- Treat as VM-internal.
- Do not write here from Forth0 programs unless you are explicitly patching code/words and know what you are doing.

### MMIO region (internal + I/O boundary)
Contains handshake flags/fields for input/output and HALT.

- Used by the VM runtime and device protocols.
- Most `.f0` tests should not touch MMIO directly (they normally end by executing `HALT` word).

### Workspace region (internal baseline structures)
Contains the std7_fixed baseline data structures: ART table, variables, constants, words/images, pools, etc.

- Many ART entries point into workspace.
- User programs should generally use ART-published addresses (e.g. `VAR_A24`, `CONST1`, `WORD_ADD24`) rather than hardcoding workspace offsets.

---

## ART table (ABI)

The ART table is the primary ABI surface: tools/tests read addresses of baseline objects from ART.

Reference:
- `doc/abi_artifacts.md`

In std7_fixed tools/tests we treat ART base as:

- `ART = align8(workspace_base + 512)`

(i.e. `ART = (workspace_base + 512 + 7) & ~7` in bitaddrs)

---

## Standardized scratch / TESTG

The baseline publishes a standardized scratch region:

- `ART_TESTSCR_BASE` (ART[63]) = `TESTSCR_BASE` (bitaddr)
- `ART_TESTSCR_END`  (ART[64]) = `TESTSCR_END`  (bitaddr, 1 past end)

Policy:
- `ART_TESTG` (ART[43]) is equal to `TESTSCR_BASE` (so `TESTG` is a standard output window base)

### Recommended rule for `.f0` tests and small programs
- Treat `[TESTSCR_BASE .. TESTSCR_END)` as your writable scratch region.
- Write test output into `TESTG` (typically the first bytes of the scratch region).
- Place temporary buffers at fixed offsets from `TESTG` **inside** the scratch region.

Many existing tests use patterns like:

- `A_base   = TESTG + 256*8`
- `B_base   = TESTG + 320*8`
- `RES_base = TESTG + 384*8`

This is fine as long as all used ranges remain `< TESTSCR_END`.

---

## Devices / bus

Devices are published via ART:

- `ART_BUS_BASE`   (ART[65]) = `BUS_BASE`
- `ART_TERM0_DESC` (ART[66]) = `TERM0_DESC`

Reference:
- `doc/devices.md`

Guideline:
- treat the bus/device descriptor area as VM-/device-owned unless you implement a device protocol.

---

## Block pointers (2b)

Block pointers are bitaddrs aligned to 32 bits:

- `P % 32 == 0`  (low5 == 0)

24-bit values in a block at `P` use:
- data bits:    `[P + 0 .. P + 23]`
- padding bits: `[P + 24 .. P + 31]` (reserved; should be preserved by 24-bit store)

Pointer primitives:
- `LOAD24AP/LOAD24BP` read 24 bits from `*AP/*BP` (ignore padding)
- `STORE24RP` writes 24 bits to `*RP` (preserve padding)

Host-side strict check for pointer literals:
- `F0C_STRICT_ALIGN32=1 build/bin/forth0c ...`
will error on unaligned `LITAP/LITBP/LITRP` immediates.

