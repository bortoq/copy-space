#!/bin/sh
set -eu

# Stage-23 completion hard-block is satisfied only when core executable gates are green.
sh scripts/tdd/test_rv32_stage23_policy_block.sh >/dev/null
sh scripts/tdd/test_rv32_stage20_closure.sh >/dev/null

echo "OK rv32 stage23 completion rule"
