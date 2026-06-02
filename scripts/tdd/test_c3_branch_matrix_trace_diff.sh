#!/bin/sh
set -eu
mkdir -p tmp/c3
cat > tmp/c3/branch_ref.json << 'JSON'
[
  {"step":0,"mode":"native","guest_pc":0,"instr_name":"bne","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"step":1,"mode":"native","guest_pc":4,"instr_name":"blt","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"step":2,"mode":"native","guest_pc":8,"instr_name":"bge","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"step":3,"mode":"native","guest_pc":12,"instr_name":"bltu","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"step":4,"mode":"native","guest_pc":16,"instr_name":"bgeu","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"step":5,"mode":"native","guest_pc":20,"instr_name":"jalr","rd":9,"rd_value":36,"mem_write":null,"stop_reason":1}
]
JSON
cp tmp/c3/branch_ref.json tmp/c3/branch_c3.json
python3 scripts/riscv/c3_trace_diff.py --c3-trace tmp/c3/branch_c3.json --ref-trace tmp/c3/branch_ref.json >/dev/null
echo "OK c3 branch matrix trace diff"
