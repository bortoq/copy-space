#!/bin/sh
set -eu
sh scripts/tdd/test_c3_trap_stop_abi.sh >/dev/null
sh scripts/tdd/test_c3_mem_align_fault.sh >/dev/null
sh scripts/tdd/test_c3_mem_bounds_fault.sh >/dev/null
sh scripts/tdd/test_c3_arith_fault.sh >/dev/null
echo "OK rv32 service trap conformance"
