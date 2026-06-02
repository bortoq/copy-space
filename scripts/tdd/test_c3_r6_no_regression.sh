#!/bin/sh
set -eu

scripts/tdd/run_rv32i_minimal.sh >/dev/null

echo "OK c3 r6 no-regression"
