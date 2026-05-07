# Memory layout / regions (std7_fixed)

_file: doc/memory_layout.md_

This document states **what `.f0` programs/tests are allowed to touch** and what `std7_fixed` guarantees.

The VM memory is **bit-addressable**:
- addresses are **bitaddrs** (bit offsets into `space`)
- byte offset is: `byte = bitaddr / 8`

---

## Guaranteed writable region for user code: TESTSCR

`std7_fixed` publishes a standardized scratch region:

- `TESTSCR_BASE` = `ART_TESTSCR_BASE` (ART[63]) (bitaddr)
- `TESTSCR_END`  = `ART_TESTSCR_END`  (ART[64]) (bitaddr, 1 past end)

Policy:
- `TESTG == TESTSCR_BASE` (ART[43])

### Guarantees (std7_fixed)
For the default baseline image:
- `TESTSCR_BASE` and `TESTSCR_END` are **byte-aligned** (`%8==0`) and **64-bit aligned** (`%64==0`)
- `TESTSCR_END > TESTSCR_BASE`
- scratch size is at least **8 KiB**:
  - `(TESTSCR_END - TESTSCR_BASE)/8 >= 8192`

This region is intended for:
- test output (write into the first bytes starting at `TESTG`)
- temporary buffers (place them at fixed offsets from `TESTG` inside the region)

### Practical convention used by existing tests
Many tests use offsets like:
- `A_base   = TESTG + 256*8`
- `B_base   = TESTG + 320*8`
- `RES_base = TESTG + 384*8`

This is safe as long as all accessed ranges remain `< TESTSCR_END`.

---

## ART table (ABI surface)

The ART table is the primary ABI surface: tools/tests read addresses of baseline objects from ART.

Reference:
- `doc/abi_artifacts.md`

In std7_fixed tools/tests we treat ART base as:

- `ART = align8(workspace_base + 512)`

(i.e. `ART = (workspace_base + 512 + 7) & ~7` in bitaddrs)

---

## Devices / bus (published, but not scratch)

Devices are published via ART:

- `BUS_BASE`   = ART[65]
- `TERM0_DESC` = ART[66]

Reference:
- `doc/devices.md`

Guideline:
- treat the bus/device descriptor area as **device-owned**, not general scratch.

---

## What is NOT guaranteed / do not touch directly

### Processor region and MMIO
- treat as VM-internal and protocol-owned

### Internal workspace layout
- do not hardcode internal offsets into workspace
- use ART-published addresses instead

See stability notes:
- `doc/stability.md`

---

## Tests enforcing these guarantees
- TDD: `scripts/tdd/test_memory_layout_guarantees.sh`

