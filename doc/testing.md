# Testing

_file: doc/testing.md_

This repo uses a **forth0-first** testing workflow: most tests are `.f0` programs compiled by `forth0c` and executed via the VM pipeline.

---

## Quick commands

Build binaries:

    make bins

Run main regression tests:

    make test

Run engineering / TDD tests:

    make tdd

Build legacy C token-generators (optional):

    make tok
    # or
    make TOK=1 bins

---

## What is the difference between `make test` and `make tdd`?

### `make test`
- Runs `scripts/test_all.sh`.
- Intended to be the main “does the repo work?” check.
- Produces fail bundles on mismatch (see below).

### `make tdd`
- Runs `scripts/tdd/run_all.sh`.
- Smaller, focused engineering checks (ABI, scratch, TERM0 descriptor, forth0c smoke, etc.).
- Runs in CI on every push/PR.

---

## Forth0 execution pipeline (used by tests)

A typical `.f0` test is executed like this:

1) `mkimage_std7_fixed` → base image `std7.bin`
2) `forth0c` compiles `.f0` → `.tok` (token stream)
3) `vmrun` (compile phase) applies `.tok` to `std7.bin` and produces `compiled_space.bin`
4) `vmprep_forth0` prepares `compiled_space.bin` for run (boot + VAR_IP setup)
5) `vmrun` (run phase) executes until `MMIO.HALT`, producing `after.bin`
6) harness reads bytes from `TESTG` and compares to expected bytes

---

## Running a single test

### `make test` (single case)
`script/test_all.sh` supports `ONLY=<name>`:

    ONLY=eq24 make test

(Names are the `maybe_run "<name>" ...` entries in `scripts/test_all.sh`.)

### TDD scripts
You can run any TDD script directly:

    sh scripts/tdd/test_forth0_2a.sh

---

## Debug helper: run one `.f0` and dump `TESTG`

Use:

    scripts/forth0/run_f0.sh --in src/forth0/tests/test_eq24.f0 --dump-testg 4

With expected bytes:

    scripts/forth0/run_f0.sh --in src/forth0/tests/test_eq24.f0 --dump-testg 4 --expect-hex 80008000

Keep temp logs/artifacts:

    scripts/forth0/run_f0.sh --in src/forth0/tests/test_add24p_via_prims.f0 --dump-testg 64 --keep

Artifacts/logs will be kept under:

- `tmp/f0run/`

---

## Fail bundles

`scripts/test_all.sh` writes fail bundles under:

- `tmp/fail/<test>_<timestamp>/`

They typically include:
- `tok.bin` (generated tokens)
- `compiled_space.bin`
- `after.bin`
- `compile.log`, `prep.log`, `run.log`
- `got.bin` / `exp.bin`
- input images used (`out/img_fixed_pool_small.bin`, `out/img_fixed_pool_big.bin`), if present

This is meant to make debugging reproducible: you can re-run the pipeline on the saved artifacts.

---

## CI

GitHub Actions workflow:

- `.github/workflows/ci.yml`

Runs:
- `make bins`
- ABI artifacts doc sync (`scripts/check_art_doc_sync.py --doc doc/abi_artifacts.md`)
- `make test`
- `make tdd`

