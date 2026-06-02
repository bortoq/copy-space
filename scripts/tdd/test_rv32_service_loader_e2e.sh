#!/bin/sh
set -eu
sh scripts/tdd/test_rv32m_loader_happy_path.sh >/dev/null
sh scripts/tdd/test_rv32m_loader_integrity.sh >/dev/null
sh scripts/tdd/test_rv32m_loader_reproducibility.sh >/dev/null
echo "OK rv32 service loader e2e"
