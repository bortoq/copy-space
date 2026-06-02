#!/bin/sh
set -eu

mkdir -p tmp/c3

cat > tmp/c3/decode_ref.json << 'JSON'
[
  {"guest_pc":0,"instr_name":"decode_known","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"guest_pc":4,"instr_name":"decode_unknown","rd":null,"rd_value":null,"mem_write":null,"stop_reason":3}
]
JSON

cp tmp/c3/decode_ref.json tmp/c3/decode_c3.json
python3 scripts/riscv/c3_trace_diff.py --c3-trace tmp/c3/decode_c3.json --ref-trace tmp/c3/decode_ref.json >/dev/null

echo "OK c3 decode trace diff"
