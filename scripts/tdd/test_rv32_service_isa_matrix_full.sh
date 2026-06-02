#!/bin/sh
set -eu
sh scripts/tdd/test_rv32_service_isa_matrix.sh >/dev/null
# Extra full-profile smoke from existing M/closure gates.
sh scripts/tdd/test_c3_rv32i_closure_audit.sh >/dev/null
sh scripts/tdd/test_c3_rv32m_verification_matrix.sh >/dev/null
echo "OK rv32 service isa matrix full"
