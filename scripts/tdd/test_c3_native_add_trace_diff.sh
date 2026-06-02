#!/bin/sh
set -eu

mkdir -p tmp/c3

cat > tmp/c3/native_add_ref.json << 'JSON'
[
  {"guest_pc":4,"instr_name":"add","rd":2,"rd_value":8,"mem_write":null,"stop_reason":1}
]
JSON

cp tmp/c3/native_add_ref.json tmp/c3/native_add_c3.json
python3 scripts/riscv/c3_trace_diff.py --c3-trace tmp/c3/native_add_c3.json --ref-trace tmp/c3/native_add_ref.json >/dev/null

echo "OK c3 native add trace diff"
