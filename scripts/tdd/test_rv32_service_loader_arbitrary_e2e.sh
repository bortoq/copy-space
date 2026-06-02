#!/bin/sh
set -eu
sh scripts/tdd/test_rv32_service_loader_e2e.sh >/dev/null
sh scripts/tdd/test_rv32m_unified_entrypoint.sh >/dev/null
sh scripts/tdd/test_rv32m_slice_independence.sh >/dev/null
echo "OK rv32 service loader arbitrary e2e"
