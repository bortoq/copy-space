#!/bin/sh
set -eu

# Loop behavior is covered by native end-to-end run plus budget gate.
sh scripts/tdd/test_c3_mvp5_native_e2e.sh
sh scripts/tdd/test_c3_budget.sh

echo "OK c3 interpreter loop"
