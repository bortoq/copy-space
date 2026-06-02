#!/bin/sh
set -eu
sh scripts/tdd/test_rv32_service_trace_diff_full.sh >/dev/null
echo "OK rv32 service ext decode order"
