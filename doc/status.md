# Status — std7_fixed + forth0 — 2026-05-07

_file: doc/status.md_

This is a **status/progress** document (what is done and how it is tested), not a long-term plan.
For plans: `doc/roadmap.md`.

Legend:
- `[x]` done (with stable tests / usage)
- `[~]` partial / could be improved
- `[ ]` not done / deferred

---

## Where tests live

- Forth0 libs: `src/forth0/lib/`
- Forth0 tests: `src/forth0/tests/`
- TDD harness scripts: `scripts/tdd/test_forth0*.sh`
- Main regression harness: `scripts/test_all.sh`
- Runner: `scripts/tdd/run_all.sh`

---

## A) Engineering baseline

- [x] `VM_ERR` diagnostics covered by TDD:
  - `scripts/tdd/test_vmerr_diag.sh`

- [x] Standardized test scratch:
  - policy: `ART_TESTG == ART_TESTSCR_BASE`
  - `ART_TESTSCR_BASE/ART_TESTSCR_END` (ART[63..64])
  - TDD:
    - `scripts/tdd/test_scratch_abi.sh`
    - `scripts/tdd/test_scratch_artifacts.sh`

- [x] TERM0 descriptor ABI (devices/bus baseline):
  - TDD: `scripts/tdd/test_term0_desc_abi.sh`
  - doc: `doc/devices.md`

- [x] Fail bundles:
  - TDD: `scripts/tdd/test_fail_bundle.sh`
  - fail bundles produced by: `scripts/test_all.sh` → `tmp/fail/...`

- [x] vmrep tooling selftest:
  - TDD: `scripts/tdd/test_vmrep_tools.sh`

- [x] ABI artifacts doc sync:
  - TDD: `scripts/tdd/test_art_doc_sync.sh`
  - doc: `doc/abi_artifacts.md`

- [x] CI:
  - `.github/workflows/ci.yml` (make bins / make test / make tdd / ABI doc sync)

---

## B) 2b pointers (block pointers)

### Base ptr words / primitives
- [x] `LITAP/LITBP/LITRP`, `VAR_AP/VAR_BP/VAR_RP` (ART[55..60])
- [x] `LOAD24AP/LOAD24BP/STORE24RP` (ART[67..69])
- [x] Padding semantics:
  - Forth0 test: `src/forth0/tests/test_ptrprims_padding.f0`
  - TDD: `scripts/tdd/test_forth0_ptrprims.sh`

### Derived pointer arithmetic (no new ART)
- [x] `INC_PTR32` (derived):
  - Forth0 test: `src/forth0/tests/test_incptr32.f0`
  - TDD: `scripts/tdd/test_forth0_ptr32.sh`
- [x] `ADD_PTR_CONST32` (derived):
  - Forth0 test: `src/forth0/tests/test_addptr_const32.f0`
  - TDD: `scripts/tdd/test_forth0_ptr32.sh`

### Derived pointer-based ops (via primitives)
- [x] `ADD24P` via prims:
  - Forth0 test: `src/forth0/tests/test_add24p_via_prims.f0`
  - TDD: `scripts/tdd/test_forth0_add24p.sh`
- [x] `LT24P` via prims:
  - Forth0 test: `src/forth0/tests/test_lt24p_via_prims.f0`
  - TDD: `scripts/tdd/test_forth0_lt24p.sh`
- [x] `EQ24P` test:
  - Forth0 test: `src/forth0/tests/test_eq24p.f0`
  - TDD: `scripts/tdd/test_forth0_ptrprims.sh`

### Alignment contract
- [x] Optional strict host-side check:
  - `F0C_STRICT_ALIGN32=1`
  - negative TDD: `scripts/tdd/test_forth0c_strict.sh`
- [ ] VM runtime checks (not required for baseline)

### Deferred
- [ ] Raw bit pointers / bit pointers (not required for block-pointer baseline)

---

## Forth0-first baseline

- [x] Host compiler: `build/bin/forth0c` (implementation: `src/forth0/host/`)
- [x] Execution pipeline documented:
  - `doc/forth0.md`
  - `doc/testing.md`
- [x] `make test` and `make tdd` run `.f0` tests (forth0-first)
- [x] Legacy C token-generators are optional:
  - `make tok`
  - `make TOK=1 bins`

---

## 2a arithmetic (baseline)

- [x] Forth0 tests:
  - `src/forth0/tests/test_add24.f0`
  - `src/forth0/tests/test_eq24.f0`
  - `src/forth0/tests/test_lt24.f0`
  - TDD: `scripts/tdd/test_forth0_2a.sh`

- [x] Bit-level regression tests (Forth0):
  - `src/forth0/tests/test_fulladder.f0`
  - `src/forth0/tests/test_add8.f0`
  - TDD: `scripts/tdd/test_forth0_bitops.sh`

