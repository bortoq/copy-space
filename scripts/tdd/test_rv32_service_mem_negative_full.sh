#!/bin/sh
set -eu
sh scripts/tdd/test_c3_mem_align_fault.sh >/dev/null
sh scripts/tdd/test_c3_mem_bounds_fault.sh >/dev/null
sh scripts/tdd/test_c3_mem_subword.sh >/dev/null
sh scripts/tdd/test_vmerr_diag.sh >/dev/null
echo "OK rv32 service mem negative full"
