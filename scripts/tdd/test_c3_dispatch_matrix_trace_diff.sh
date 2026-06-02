#!/bin/sh
set -eu

mkdir -p tmp/c3

cat > tmp/c3/dispatch_ref.json << 'JSON'
[
  {"guest_pc":0, "instr_name":"dispatch_addi", "rd":null, "rd_value":null, "mem_write":null, "stop_reason":null},
  {"guest_pc":4, "instr_name":"dispatch_add",  "rd":null, "rd_value":null, "mem_write":null, "stop_reason":null},
  {"guest_pc":8, "instr_name":"dispatch_sw",   "rd":null, "rd_value":null, "mem_write":null, "stop_reason":null},
  {"guest_pc":12,"instr_name":"dispatch_beq",  "rd":null, "rd_value":null, "mem_write":null, "stop_reason":null},
  {"guest_pc":16,"instr_name":"dispatch_jal",  "rd":null, "rd_value":null, "mem_write":null, "stop_reason":null},
  {"guest_pc":24,"instr_name":"dispatch_unknown","rd":null,"rd_value":null,"mem_write":null,"stop_reason":3}
]
JSON

cp tmp/c3/dispatch_ref.json tmp/c3/dispatch_c3.json
python3 scripts/riscv/c3_trace_diff.py --c3-trace tmp/c3/dispatch_c3.json --ref-trace tmp/c3/dispatch_ref.json >/dev/null

echo "OK c3 dispatch matrix trace diff"
