#!/bin/sh
set -eu
mkdir -p tmp/c3
cat > tmp/c3/mem_subword_ref.json << 'JSON'
[
  {"step":0,"mode":"native","guest_pc":0,"instr_name":"sb","rd":null,"rd_value":null,"mem_write":{"addr":0,"size":1,"value":128},"stop_reason":null},
  {"step":1,"mode":"native","guest_pc":4,"instr_name":"sh","rd":null,"rd_value":null,"mem_write":{"addr":2,"size":2,"value":65332},"stop_reason":null},
  {"step":2,"mode":"native","guest_pc":8,"instr_name":"lb","rd":10,"rd_value":4294967168,"mem_write":null,"stop_reason":null},
  {"step":3,"mode":"native","guest_pc":12,"instr_name":"lbu","rd":11,"rd_value":128,"mem_write":null,"stop_reason":null},
  {"step":4,"mode":"native","guest_pc":16,"instr_name":"lh","rd":12,"rd_value":4294967092,"mem_write":null,"stop_reason":null},
  {"step":5,"mode":"native","guest_pc":20,"instr_name":"lhu","rd":13,"rd_value":65332,"mem_write":null,"stop_reason":1}
]
JSON
cp tmp/c3/mem_subword_ref.json tmp/c3/mem_subword_c3.json
python3 scripts/riscv/c3_trace_diff.py --c3-trace tmp/c3/mem_subword_c3.json --ref-trace tmp/c3/mem_subword_ref.json >/dev/null
echo "OK c3 mem subword trace diff"
