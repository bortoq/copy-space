#!/bin/sh
set -eu

sh scripts/tdd/test_rv32m_m_semantics_vectors.sh
sh scripts/tdd/test_c3_m_div_corner.sh
sh scripts/tdd/test_c3_m_div_corner_trace_diff.sh
sh scripts/tdd/test_c3_rv32i_closure_audit.sh

echo "OK rv32m preflight"
