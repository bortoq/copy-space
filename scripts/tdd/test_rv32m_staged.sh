#!/bin/sh
set -eu

RV32M_STAGED_REPEATS=3 sh scripts/tdd/run_rv32m_staged.sh >/dev/null

test -f tmp/rv32m_staged_run_1.log
test -f tmp/rv32m_staged_run_2.log
test -f tmp/rv32m_staged_run_3.log

echo "OK rv32m staged 3/3"
