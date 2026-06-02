#!/bin/sh
set -eu

mkdir -p tmp/c3_repro_test

# Positive path: exact ref should pass and produce outdir artifacts.
cat > tmp/c3_repro_test/ref_ok.json << 'JSON'
[
  {"step":0,"mode":"native","guest_pc":0,"instr_name":"addi","rd":1,"rd_value":5,"mem_write":null,"stop_reason":null},
  {"step":1,"mode":"native","guest_pc":4,"instr_name":"add","rd":2,"rd_value":8,"mem_write":null,"stop_reason":null},
  {"step":2,"mode":"native","guest_pc":8,"instr_name":"sw","rd":null,"rd_value":null,"mem_write":{"addr":0,"size":4,"value":8},"stop_reason":null},
  {"step":3,"mode":"native","guest_pc":12,"instr_name":"beq","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"step":4,"mode":"native","guest_pc":20,"instr_name":"jal","rd":5,"rd_value":20,"mem_write":null,"stop_reason":1}
]
JSON

scripts/riscv/c3_run_and_diff.sh --case mvp5 --mode native --ref-trace tmp/c3_repro_test/ref_ok.json --outdir tmp/c3_repro_test/ok >/dev/null

# Negative path: introduce mismatch, must fail and create repro bundle.
cat > tmp/c3_repro_test/ref_bad.json << 'JSON'
[
  {"step":0,"mode":"native","guest_pc":0,"instr_name":"addi","rd":1,"rd_value":6,"mem_write":null,"stop_reason":null}
]
JSON

set +e
scripts/riscv/c3_run_and_diff.sh --case mvp5 --mode native --ref-trace tmp/c3_repro_test/ref_bad.json --outdir tmp/c3_repro_test/bad >/dev/null 2>&1
rc=$?
set -e
[ "$rc" -ne 0 ]

test -f tmp/c3_repro_test/bad/c3_trace.json
test -f tmp/c3_repro_test/bad/ref_trace.json
test -f tmp/c3_repro_test/bad/diff.txt
test -f tmp/c3_repro_test/bad/meta.json
test -f tmp/c3_repro_test/bad/stop_dump.bin

echo "OK c3 native repro"
