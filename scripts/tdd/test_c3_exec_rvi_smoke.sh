#!/bin/sh
set -eu

sh scripts/tdd/test_c3_exec_mvp5.sh
sh scripts/tdd/test_c3_native_add.sh
sh scripts/tdd/test_c3_native_addi.sh
sh scripts/tdd/test_c3_native_beq.sh
sh scripts/tdd/test_c3_native_jal.sh
sh scripts/tdd/test_c3_native_sw.sh
sh scripts/tdd/test_c3_mem_subword.sh

echo "OK c3 exec rvi smoke"
