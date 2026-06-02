#!/bin/sh
set -eu
sh scripts/tdd/test_c3_budget.sh >/dev/null
sh scripts/tdd/test_c3_rv32m_budget_freeze.sh >/dev/null
echo "OK rv32 service slo"
