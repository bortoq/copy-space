#!/bin/sh
set -eu

sh scripts/tdd/test_rv32_space_align_fault.sh
sh scripts/tdd/test_rv32_space_bounds_fault.sh
sh scripts/tdd/test_rv32_space_trace_proof.sh
sh scripts/tdd/test_rv32_space_control_proof.sh

echo "OK rv32 space closure"
