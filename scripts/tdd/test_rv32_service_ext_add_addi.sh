#!/bin/sh
set -eu

# Stage-20 replacement gate:
# no host RV trace/emulation path; verify in-space runtime path + loader/channel stack.
sh scripts/tdd/test_rv32m_unified_entrypoint.sh >/dev/null
sh scripts/tdd/test_rv32m_loop_smoke.sh >/dev/null
sh scripts/tdd/test_rv32m_channel_abi_contract.sh >/dev/null

echo "OK rv32 service ext add/addi (in-space replacement)"
