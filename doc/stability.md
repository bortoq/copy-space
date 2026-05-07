# Stability / guarantees

_file: doc/stability.md_

This document states what is intended to be stable, and what is not.

The goal is to keep the VM core small and evolve higher-level logic mostly via `.f0` programs.

---

## Stable (baseline contract)

### ART ABI is append-only
- `doc/abi_artifacts.md` is the ABI reference.
- New ART entries may be appended; existing indices should not change meaning.
- CI/TDD checks `doc/abi_artifacts.md` covers `ART[0..ART_COUNT-1]`.

### Standardized test scratch / TESTG
- `TESTSCR_BASE/END` (ART[63..64]) define a writable scratch region.
- Policy: `TESTG == TESTSCR_BASE` (ART[43]).

### TERM0 descriptor ABI (baseline devices)
- `BUS_BASE` / `TERM0_DESC` are published via ART[65..66].
- ABI is validated by TDD (`scripts/tdd/test_term0_desc_abi.sh`).

### Forth0 toolchain and `.f0` syntax (v0)
We treat the current `forth0c` `.f0` syntax as a stable “v0” interface:
- `include`, `const`, `emit`
- `copybits`, `setbit/setbyte/set24`
- `macro ... endmacro`, calls `NAME(expr,...)`
- `for ... endfor` (compile-time loop)

See:
- `doc/forth0.md`
- `doc/forth0_howto.md`

### Test harnesses
- `make test` and `make tdd` should remain stable entry points.
- Fail bundles under `tmp/fail/` are part of the debugging workflow.

---

## Implementation-defined / not stable (avoid relying on it)

### Same-tick write conflict resolution
Programs should not rely on conflict resolution semantics inside a tick.
Treat conflicting schedules as invalid.

See:
- `doc/semantics.md`

### Internal workspace layout
Do not hardcode internal offsets inside workspace.
Use ART-published addresses and standardized scratch.

---

## Planned (not yet stabilized)

- Unified benchmark CSV schema enforcement (currently “target v0”, migration ongoing).
- Copy-flow manager / automatic layer partitioning (scheduler) for copy plans.

