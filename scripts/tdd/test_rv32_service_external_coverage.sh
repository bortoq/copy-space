#!/bin/sh
set -eu
sh scripts/tdd/test_rv32m_external_e2e_coverage.sh >/dev/null
echo "OK rv32 service external coverage"
