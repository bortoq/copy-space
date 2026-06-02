#!/bin/sh
set -eu
sh scripts/tdd/test_rv32m_external_e2e_smoke.sh >/dev/null
echo "OK rv32 service external smoke"
