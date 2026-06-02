#!/bin/sh
set -eu
# Fuzz smoke via malformed image/header vectors and negative loader path.
sh scripts/tdd/test_rv32m_image_format_contract.sh >/dev/null
sh scripts/tdd/test_rv32_service_loader_negative.sh >/dev/null
echo "OK rv32 service fuzz smoke"
