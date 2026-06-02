#!/usr/bin/env bash
set -euo pipefail

DOC="doc/freertos_build_profile.md"

[ -f "$DOC" ]

rg -q 'Architecture: `rv32im`' "$DOC"
rg -q 'ABI: `ilp32`' "$DOC"
rg -q 'Endianness: little-endian' "$DOC"
rg -q 'Calling convention: RISC-V ELF psABI for RV32 `ilp32`' "$DOC"

rg -q '\.text/\.rodata' "$DOC"
rg -q '\.data' "$DOC"
rg -q '\.bss' "$DOC"
rg -q 'heap' "$DOC"
rg -q 'stack' "$DOC"
rg -q 'Entry point contract' "$DOC"

rg -q '_start' "$DOC"
rg -q 'vTaskStartScheduler\(\)' "$DOC"
rg -q 'No host Python/shell/Forth0 helper' "$DOC"
rg -q 'LOAD_CODE/RUN/STEP/READ_REGS/READ_MEM/WRITE_MEM' "$DOC"

echo "OK rv32 freertos build profile"
