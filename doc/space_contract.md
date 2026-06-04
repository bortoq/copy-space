# Space Contract

`src/vm/space.*` defines the emulator of the address space.

The contract is stable:

- The functional behavior of the emulator must not change.
- Allowed changes are limited to:
  - performance improvements,
  - portability improvements,
  - reliability improvements,
  - diagnostics improvements,
  - maintainability improvements,
  - testability improvements.
- Any change that alters observable space semantics must be treated as a separate project decision, not a refactoring.
- `space.*` must remain only the address-space emulator.
- `space.*` must not contain or accumulate residual logic from:
  - proofs or checks,
  - alternative emulators,
  - `forth0`,
  - `RISC-V` toolchains,
  - orchestration code,
  - compiler/runtime helpers,
  - test harness internals.
- Any such functionality belongs outside `space.*` and must be implemented in separate source boundaries.

The emulator must continue to provide:

- copying of semi-intervals in bit space,
- copy-in/copy-out through stdin/stdout channels,
- loading of a single boot instruction before the first tick,
- bounded execution by the tick count passed at launch,
- resident minimal host interaction only.

This contract is the boundary for future iterations.
