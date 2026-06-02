#!/bin/sh
set -eu

# Validate external binary path and release-style e2e gates.
sh scripts/tdd/test_rv32m_external_e2e_smoke.sh
sh scripts/tdd/test_rv32m_external_e2e_coverage.sh

echo "OK c3 external binary e2e"
