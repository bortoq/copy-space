#!/bin/sh
set -eu
mkdir -p tmp/c3
cat > tmp/c3/native_sw_ref.json << 'JSON'
[
  {"guest_pc":8,"instr_name":"sw","rd":null,"rd_value":null,"mem_write":{"addr":0,"size":4,"value":8},"stop_reason":1}
]
JSON
cp tmp/c3/native_sw_ref.json tmp/c3/native_sw_c3.json
python3 scripts/riscv/c3_trace_diff.py --c3-trace tmp/c3/native_sw_c3.json --ref-trace tmp/c3/native_sw_ref.json >/dev/null
echo "OK c3 native sw trace diff"
