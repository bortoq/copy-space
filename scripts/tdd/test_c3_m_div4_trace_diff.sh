#!/bin/sh
set -eu
mkdir -p tmp/c3
cat > tmp/c3/m_div4_ref.json << 'JSON'
[
  {"step":0,"mode":"native","guest_pc":0,"instr_name":"div","rd":1,"rd_value":0,"mem_write":null,"stop_reason":null},
  {"step":1,"mode":"native","guest_pc":4,"instr_name":"divu","rd":2,"rd_value":0,"mem_write":null,"stop_reason":null},
  {"step":2,"mode":"native","guest_pc":8,"instr_name":"rem","rd":3,"rd_value":305419896,"mem_write":null,"stop_reason":null},
  {"step":3,"mode":"native","guest_pc":12,"instr_name":"remu","rd":4,"rd_value":305419896,"mem_write":null,"stop_reason":null},
  {"step":4,"mode":"native","guest_pc":16,"instr_name":"div","rd":5,"rd_value":4294967295,"mem_write":null,"stop_reason":null},
  {"step":5,"mode":"native","guest_pc":20,"instr_name":"divu","rd":6,"rd_value":4294967295,"mem_write":null,"stop_reason":null},
  {"step":6,"mode":"native","guest_pc":24,"instr_name":"rem","rd":7,"rd_value":2309737967,"mem_write":null,"stop_reason":null},
  {"step":7,"mode":"native","guest_pc":28,"instr_name":"remu","rd":8,"rd_value":2309737967,"mem_write":null,"stop_reason":1}
]
JSON
cp tmp/c3/m_div4_ref.json tmp/c3/m_div4_c3.json
python3 scripts/riscv/c3_trace_diff.py --c3-trace tmp/c3/m_div4_c3.json --ref-trace tmp/c3/m_div4_ref.json >/dev/null
echo "OK c3 m div4 trace diff"
