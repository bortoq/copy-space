#!/bin/sh
set -eu

sh scripts/tdd/test_rv32_c3_dispatch_contract.sh >/dev/null
sh scripts/tdd/test_c3_real_addi.sh >/dev/null

echo "OK c3 real smoke"
