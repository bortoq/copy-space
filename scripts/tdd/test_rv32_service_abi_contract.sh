#!/bin/sh
set -eu
rg -n "LOAD_IMAGE|LOAD_CODE|RUN|STEP|STOP|STATUS|READ_MEM|WRITE_MEM|READ_REGS|max_ticks|watchdog_ticks" doc/rv32_service_abi.md >/dev/null
sh scripts/tdd/test_rv32m_channel_abi_contract.sh >/dev/null
sh scripts/tdd/test_rv32m_image_format_contract.sh >/dev/null
echo "OK rv32 service abi contract"
