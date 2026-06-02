#!/bin/sh
set -eu
mkdir -p tmp/c3_m_diff
cat > tmp/c3_m_diff/ref_m_fastpath.json << 'JSON'
[
  {"step":0,"mode":"native","guest_pc":0,"instr_name":"mul","rd":1,"rd_value":0,"mem_write":null,"stop_reason":null},
  {"step":1,"mode":"native","guest_pc":4,"instr_name":"mul","rd":2,"rd_value":305419896,"mem_write":null,"stop_reason":null},
  {"step":2,"mode":"native","guest_pc":8,"instr_name":"div","rd":3,"rd_value":2309737967,"mem_write":null,"stop_reason":null},
  {"step":3,"mode":"native","guest_pc":12,"instr_name":"div","rd":4,"rd_value":4294967295,"mem_write":null,"stop_reason":null},
  {"step":4,"mode":"native","guest_pc":16,"instr_name":"rem","rd":5,"rd_value":2309737967,"mem_write":null,"stop_reason":null},
  {"step":5,"mode":"native","guest_pc":20,"instr_name":"div","rd":6,"rd_value":2147483648,"mem_write":null,"stop_reason":null},
  {"step":6,"mode":"native","guest_pc":24,"instr_name":"rem","rd":7,"rd_value":0,"mem_write":null,"stop_reason":null},
  {"step":7,"mode":"native","guest_pc":28,"instr_name":"mul","rd":8,"rd_value":4294967294,"mem_write":null,"stop_reason":1}
]
JSON
scripts/riscv/c3_run_and_diff.sh --case m_fastpath --mode native --ref-trace tmp/c3_m_diff/ref_m_fastpath.json --outdir tmp/c3_m_diff/run >/dev/null
test -f tmp/c3_m_diff/run/runtime/testg.bin
echo "OK c3 m run+diff"
