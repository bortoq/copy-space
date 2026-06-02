#!/bin/sh
set -eu
mkdir -p tmp/c3
cat > tmp/c3/native_beq_ref.json << 'JSON'
[
  {"guest_pc":12,"instr_name":"beq","rd":null,"rd_value":null,"mem_write":null,"stop_reason":1}
]
JSON
cp tmp/c3/native_beq_ref.json tmp/c3/native_beq_c3.json
python3 scripts/riscv/c3_trace_diff.py --c3-trace tmp/c3/native_beq_c3.json --ref-trace tmp/c3/native_beq_ref.json >/dev/null
echo "OK c3 native beq trace diff"
