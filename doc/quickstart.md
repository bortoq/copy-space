# Quickstart

## Build

Build binaries:

    make bins

## Run the demo (CSV)

Run the demo (writes CSV to tmp/demo.csv):

    scripts/demo_db.sh > /dev/null 2> tmp/demo.stderr
    cat tmp/demo.csv

What to look at:
- `vmrep_avg_bits_uniq_dst_per_tick` (effective unique destination bits written per tick)

## Run tests

Main tests:

    make test

Engineering / TDD tests:

    make tdd

## Scripts

Production scripts live in scripts/, historical patch scripts in scripts/old/
