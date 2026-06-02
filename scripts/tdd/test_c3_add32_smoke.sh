#!/bin/sh
set -eu

# Minimal arithmetic primitive smoke for C3.
sh scripts/tdd/test_c3_native_add.sh
sh scripts/tdd/test_c3_native_addi.sh

echo "OK c3 add32 smoke"
