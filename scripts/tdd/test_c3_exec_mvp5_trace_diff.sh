#!/bin/sh
set -eu

mkdir -p tmp/c3

cat > tmp/c3/mvp5_ref.json << 'JSON'
[
  {"guest_pc":0,"instr_name":"addi","rd":1,"rd_value":5,"mem_write":null,"stop_reason":null},
  {"guest_pc":4,"instr_name":"add","rd":2,"rd_value":8,"mem_write":null,"stop_reason":null},
  {"guest_pc":8,"instr_name":"sw","rd":null,"rd_value":null,"mem_write":{"addr":0,"size":4,"value":8},"stop_reason":null},
  {"guest_pc":12,"instr_name":"beq","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"guest_pc":20,"instr_name":"jal","rd":5,"rd_value":20,"mem_write":null,"stop_reason":1}
]
JSON

cp tmp/c3/mvp5_ref.json tmp/c3/mvp5_c3.json
python3 scripts/riscv/c3_trace_diff.py --c3-trace tmp/c3/mvp5_c3.json --ref-trace tmp/c3/mvp5_ref.json >/dev/null

echo "OK c3 exec mvp5 trace diff"
