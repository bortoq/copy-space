#!/bin/sh
set -eu
# Space core semantics guard via existing VM diagnostics/contracts.
sh scripts/tdd/test_vmerr_diag.sh >/dev/null
sh scripts/tdd/test_rv32m_image_format_contract.sh >/dev/null
sh scripts/tdd/test_rv32m_channel_abi_contract.sh >/dev/null
echo "OK rv32 service space contract unchanged"
