#!/bin/sh
set -eu

mkdir -p tmp/c3_mem_diff
cat > tmp/c3_mem_diff/ref_mem.json << 'JSON'
[
  {"step":0,"mode":"native","guest_pc":0,"instr_name":"sw","rd":null,"rd_value":null,"mem_write":{"addr":0,"size":4,"value":42},"stop_reason":null},
  {"step":1,"mode":"native","guest_pc":4,"instr_name":"lw","rd":1,"rd_value":42,"mem_write":null,"stop_reason":1}
]
JSON

scripts/riscv/c3_run_and_diff.sh --case mem_sw_lw --mode native --ref-trace tmp/c3_mem_diff/ref_mem.json --outdir tmp/c3_mem_diff/run >/dev/null

test -f tmp/c3_mem_diff/run/runtime/testg.bin

echo "OK c3 mem run+diff"
