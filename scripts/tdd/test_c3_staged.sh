#!/bin/sh
set -eu

C3_STAGED_REPEATS=3 sh scripts/tdd/run_c3_staged.sh >/dev/null

test -f tmp/c3_staged_run_1.log
test -f tmp/c3_staged_run_2.log
test -f tmp/c3_staged_run_3.log

echo "OK c3 staged 3/3"
