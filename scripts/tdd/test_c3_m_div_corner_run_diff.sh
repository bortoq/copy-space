#!/bin/sh
set -eu
mkdir -p tmp/c3_m_div_corner_diff
cat > tmp/c3_m_div_corner_diff/ref_m_div_corner.json << 'JSON'
[
  {"step":0,"mode":"native","guest_pc":0,"instr_name":"div","rd":1,"rd_value":2147483648,"mem_write":null,"stop_reason":null},
  {"step":1,"mode":"native","guest_pc":4,"instr_name":"rem","rd":2,"rd_value":0,"mem_write":null,"stop_reason":null},
  {"step":2,"mode":"native","guest_pc":8,"instr_name":"div","rd":3,"rd_value":0,"mem_write":null,"stop_reason":null},
  {"step":3,"mode":"native","guest_pc":12,"instr_name":"rem","rd":4,"rd_value":4294967295,"mem_write":null,"stop_reason":null},
  {"step":4,"mode":"native","guest_pc":16,"instr_name":"divu","rd":5,"rd_value":2147483647,"mem_write":null,"stop_reason":null},
  {"step":5,"mode":"native","guest_pc":20,"instr_name":"remu","rd":6,"rd_value":1,"mem_write":null,"stop_reason":null},
  {"step":6,"mode":"native","guest_pc":24,"instr_name":"div","rd":7,"rd_value":4294967295,"mem_write":null,"stop_reason":null},
  {"step":7,"mode":"native","guest_pc":28,"instr_name":"rem","rd":8,"rd_value":305419896,"mem_write":null,"stop_reason":1}
]
JSON
scripts/riscv/c3_run_and_diff.sh --case m_div_corner --mode native --ref-trace tmp/c3_m_div_corner_diff/ref_m_div_corner.json --outdir tmp/c3_m_div_corner_diff/run >/dev/null
test -f tmp/c3_m_div_corner_diff/run/runtime/testg.bin
echo "OK c3 m div corner run+diff"
