#!/bin/sh
set -eu
mkdir -p tmp/c3_subword_diff
cat > tmp/c3_subword_diff/ref_subword.json << 'JSON'
[
  {"step":0,"mode":"native","guest_pc":0,"instr_name":"sb","rd":null,"rd_value":null,"mem_write":{"addr":0,"size":1,"value":128},"stop_reason":null},
  {"step":1,"mode":"native","guest_pc":4,"instr_name":"sh","rd":null,"rd_value":null,"mem_write":{"addr":2,"size":2,"value":65332},"stop_reason":null},
  {"step":2,"mode":"native","guest_pc":8,"instr_name":"lb","rd":10,"rd_value":4294967168,"mem_write":null,"stop_reason":null},
  {"step":3,"mode":"native","guest_pc":12,"instr_name":"lbu","rd":11,"rd_value":128,"mem_write":null,"stop_reason":null},
  {"step":4,"mode":"native","guest_pc":16,"instr_name":"lh","rd":12,"rd_value":4294967092,"mem_write":null,"stop_reason":null},
  {"step":5,"mode":"native","guest_pc":20,"instr_name":"lhu","rd":13,"rd_value":65332,"mem_write":null,"stop_reason":1}
]
JSON
scripts/riscv/c3_run_and_diff.sh --case mem_subword --mode native --ref-trace tmp/c3_subword_diff/ref_subword.json --outdir tmp/c3_subword_diff/run >/dev/null
test -f tmp/c3_subword_diff/run/runtime/testg.bin
echo "OK c3 mem subword run+diff"
