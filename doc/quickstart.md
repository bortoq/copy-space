# Quickstart

_file: doc/quickstart.md_

## Build

Build binaries:

    make bins

## Run the demo (CSV)

Run the demo (writes CSV to `tmp/demo.csv`):

    scripts/demo_db.sh > /dev/null 2> tmp/demo.stderr
    cat tmp/demo.csv

What to look at:
- `vmrep_avg_bits_uniq_dst_per_tick` (effective unique destination bits written per tick)

## Run tests

Main regression tests:

    make test

Engineering / TDD tests:

    make tdd

## Forth0-first workflow (recommended)

Run a `.f0` program and dump `TESTG`:

    scripts/forth0/run_f0.sh --in src/forth0/tests/test_eq24.f0 --dump-testg 4

(Use `--keep` to keep logs in `tmp/f0run/`.)

Strict alignment mode for block pointers:

    F0C_STRICT_ALIGN32=1 build/bin/forth0c --image std7.bin --in prog.f0 --out prog.tok

## Legacy C token-generators (optional)

Legacy `mktok_test_*` binaries are optional:

    make tok
    # or
    make TOK=1 bins

