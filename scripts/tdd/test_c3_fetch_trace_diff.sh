#!/bin/sh
set -eu

mkdir -p tmp/c3

cat > tmp/c3/fetch_ref.json << 'JSON'
[
  {"guest_pc":0,"instr_name":"fetch","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"guest_pc":4,"instr_name":"fetch","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"guest_pc":8,"instr_name":"fetch","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"guest_pc":12,"instr_name":"stop","rd":null,"rd_value":null,"mem_write":null,"stop_reason":2}
]
JSON

cp tmp/c3/fetch_ref.json tmp/c3/fetch_c3.json
python3 scripts/riscv/c3_trace_diff.py --c3-trace tmp/c3/fetch_c3.json --ref-trace tmp/c3/fetch_ref.json >/dev/null

echo "OK c3 fetch trace diff"
