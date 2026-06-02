#!/bin/sh
set -eu
sh scripts/tdd/test_rv32m_loader_rollback.sh >/dev/null
sh scripts/tdd/test_rv32m_loader_timeout.sh >/dev/null
sh scripts/tdd/test_rv32m_image_format_contract.sh >/dev/null
echo "OK rv32 service loader negative"
