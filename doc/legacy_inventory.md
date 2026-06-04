# Legacy Inventory

This file freezes everything that is intentionally out of the active path.

## Active Minimum

The active set is intentionally small:

- `src/vm/space.c`
- `src/vm/space.h`
- `src/vm/rv32.c`
- `src/vm/rv32.h`
- `src/vm/bitcpy.c`
- `src/tools/space.c` as the active launcher on the OS side
- the active proof gates under `scripts/tdd/`
- the active documentation set listed in `doc/project_structure.md`

## Frozen Legacy

The following groups are frozen as legacy material and must not be treated as active dependencies:

- legacy `C3_RUN` proof artifacts
- legacy `FreeRTOS` integration material
- legacy `riscv-port/` migration material
- legacy `service` / `SHA` / external-corpus tracks
- retired documentation that is no longer part of the active plan
- retired `scripts/tdd/` gates that were removed from the active baseline

## Rule

If a file or directory is not listed in the active minimum, it is legacy unless the active plan explicitly reintroduces it.

`src/tools/vmrun.c` is legacy and is not part of the active minimum.
