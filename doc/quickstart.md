# Quickstart

_file: doc/quickstart.md_

## Build

Build binaries:

    make bins

## Run the demo (CSV)

Run the demo (writes CSV to tmp/demo.csv):

    scripts/demo_db.sh > /dev/null 2> tmp/demo.stderr
    cat tmp/demo.csv

What to look at:
- vmrep_avg_bits_uniq_dst_per_tick (effective unique destination bits written per tick)

## Run tests

Main regression tests:

    make test

Engineering / TDD tests:

    make tdd

Scheduler regression tests:

    ./scripts/test_scheduler.sh

## Forth0-first workflow (recommended)

Run a .f0 program and dump TESTG:

    scripts/forth0/run_f0.sh --in src/forth0/tests/test_eq24.f0 --dump-testg 4

(Use --keep to keep logs in tmp/f0run/.)

Strict alignment mode for block pointers:

    F0C_STRICT_ALIGN32=1 build/bin/forth0c --image std7.bin --in prog.f0 --out prog.tok

## Benchmarks (Python-first, recommended)

Install python package (CLI entrypoints):

    python3 -m pip install -e .

Run core benches (pack, permute, bulkcopy) into one CSV file:

    copyspace-bench-core --bench all --out tmp/bench.csv
    head -5 tmp/bench.csv

Run scheduler bench (validated scheduling, unified CSV):

    copyspace-bench-scheduler --out tmp/sched.csv --repeat 1 --inst-glob scripts/scheduler/tests/ref_pack/*.json
    head -5 tmp/sched.csv

See also: doc/benchmarks.md

## Legacy C token-generators (optional)

Legacy mktok_test_* binaries are optional:

    make tok
    # or
    make TOK=1 bins
