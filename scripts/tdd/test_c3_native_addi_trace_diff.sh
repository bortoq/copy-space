#!/bin/sh
set -eu

mkdir -p tmp/c3

cat > tmp/c3/native_addi_ref.json << 'JSON'
[
  {"guest_pc":0,"instr_name":"addi","rd":1,"rd_value":5,"mem_write":null,"stop_reason":1}
]
JSON

cp tmp/c3/native_addi_ref.json tmp/c3/native_addi_c3.json
python3 scripts/riscv/c3_trace_diff.py --c3-trace tmp/c3/native_addi_c3.json --ref-trace tmp/c3/native_addi_ref.json >/dev/null

echo "OK c3 native addi trace diff"
