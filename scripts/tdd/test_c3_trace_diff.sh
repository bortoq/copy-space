#!/bin/sh
set -eu

mkdir -p tmp/c3

cat > tmp/c3/ref.json << 'JSON'
[
  {"guest_pc":0,"instr_name":"addi","rd":1,"rd_value":42,"mem_write":null,"stop_reason":null},
  {"guest_pc":4,"instr_name":"sw","rd":null,"rd_value":null,"mem_write":{"addr":0,"size":4,"value":42},"stop_reason":null},
  {"guest_pc":8,"instr_name":"halt","rd":null,"rd_value":null,"mem_write":null,"stop_reason":1}
]
JSON

cp tmp/c3/ref.json tmp/c3/c3.json

python3 scripts/riscv/c3_trace_diff.py --c3-trace tmp/c3/c3.json --ref-trace tmp/c3/ref.json >/dev/null

echo "OK c3 trace diff"
