#!/bin/sh
set -eu

# Enforce native-only path for MVP-5.
C3_ENFORCE_NATIVE_MVP5=1 C3_MODE=native sh scripts/tdd/test_c3_exec_mvp5.sh >/dev/null

mkdir -p tmp/c3_e2e
cat > tmp/c3_e2e/ref_mvp5.json << 'JSON'
[
  {"step":0,"mode":"native","guest_pc":0,"instr_name":"addi","rd":1,"rd_value":5,"mem_write":null,"stop_reason":null},
  {"step":1,"mode":"native","guest_pc":4,"instr_name":"add","rd":2,"rd_value":8,"mem_write":null,"stop_reason":null},
  {"step":2,"mode":"native","guest_pc":8,"instr_name":"sw","rd":null,"rd_value":null,"mem_write":{"addr":0,"size":4,"value":8},"stop_reason":null},
  {"step":3,"mode":"native","guest_pc":12,"instr_name":"beq","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"step":4,"mode":"native","guest_pc":20,"instr_name":"jal","rd":5,"rd_value":20,"mem_write":null,"stop_reason":1}
]
JSON

scripts/riscv/c3_run_and_diff.sh \
  --case mvp5 \
  --mode native \
  --ref-trace tmp/c3_e2e/ref_mvp5.json \
  --outdir tmp/c3_e2e/run >/dev/null

test -f tmp/c3_e2e/run/runtime/testg.bin

echo "OK c3 mvp5 native e2e"
