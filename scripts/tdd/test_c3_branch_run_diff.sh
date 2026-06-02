#!/bin/sh
set -eu
mkdir -p tmp/c3_branch_diff
cat > tmp/c3_branch_diff/ref_branch.json << 'JSON'
[
  {"step":0,"mode":"native","guest_pc":0,"instr_name":"bne","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"step":1,"mode":"native","guest_pc":4,"instr_name":"blt","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"step":2,"mode":"native","guest_pc":8,"instr_name":"bge","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"step":3,"mode":"native","guest_pc":12,"instr_name":"bltu","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"step":4,"mode":"native","guest_pc":16,"instr_name":"bgeu","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"step":5,"mode":"native","guest_pc":20,"instr_name":"jalr","rd":9,"rd_value":36,"mem_write":null,"stop_reason":1}
]
JSON
scripts/riscv/c3_run_and_diff.sh --case branch_matrix --mode native --ref-trace tmp/c3_branch_diff/ref_branch.json --outdir tmp/c3_branch_diff/run >/dev/null
test -f tmp/c3_branch_diff/run/runtime/testg.bin
echo "OK c3 branch run+diff"
