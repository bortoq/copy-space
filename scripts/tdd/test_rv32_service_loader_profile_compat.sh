#!/bin/sh
set -eu
sh scripts/tdd/test_rv32m_image_format_contract.sh >/dev/null
sh scripts/tdd/test_rv32m_channel_abi_compat.sh >/dev/null
sh scripts/tdd/test_rv32m_channel_abi_n1_compat.sh >/dev/null
echo "OK rv32 service loader profile compat"
