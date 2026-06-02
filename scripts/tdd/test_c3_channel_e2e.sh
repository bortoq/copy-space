#!/bin/sh
set -eu

# C3 runtime uses the shared VM channel path; validate channel stack end-to-end.
sh scripts/tdd/test_rv32m_channel_abi_contract.sh
sh scripts/tdd/test_rv32m_channel_io_roundtrip.sh
sh scripts/tdd/test_rv32m_channel_stop_abi.sh

echo "OK c3 channel e2e"
