#!/bin/sh
set -eu

mkdir -p tmp/c3_repro_bundle

cat > tmp/c3_repro_bundle/ref_ok_compact.json << 'JSON'
[
  {"step":0,"guest_pc":0,"instr_name":"addi","rd":1,"rd_value":5,"mem_write":null,"stop_reason":null},
  {"step":1,"guest_pc":4,"instr_name":"add","rd":2,"rd_value":8,"mem_write":null,"stop_reason":null},
  {"step":2,"guest_pc":8,"instr_name":"sw","rd":null,"rd_value":null,"mem_write":{"addr":0,"size":4,"value":8},"stop_reason":null},
  {"step":3,"guest_pc":12,"instr_name":"beq","rd":null,"rd_value":null,"mem_write":null,"stop_reason":null},
  {"step":4,"guest_pc":20,"instr_name":"jal","rd":5,"rd_value":20,"mem_write":null,"stop_reason":1}
]
JSON

scripts/riscv/c3_run_and_diff.sh --case mvp5 --mode native --trace-mode compact --ref-trace tmp/c3_repro_bundle/ref_ok_compact.json --outdir tmp/c3_repro_bundle/ok >/dev/null

cat > tmp/c3_repro_bundle/ref_bad_compact.json << 'JSON'
[
  {"step":0,"guest_pc":0,"instr_name":"addi","rd":1,"rd_value":6,"mem_write":null,"stop_reason":null}
]
JSON

set +e
scripts/riscv/c3_run_and_diff.sh --case mvp5 --mode native --trace-mode compact --ref-trace tmp/c3_repro_bundle/ref_bad_compact.json --outdir tmp/c3_repro_bundle/bad >/dev/null 2>&1
rc=$?
set -e
[ "$rc" -ne 0 ]

test -f tmp/c3_repro_bundle/bad/c3_trace.json
test -f tmp/c3_repro_bundle/bad/ref_trace.json
test -f tmp/c3_repro_bundle/bad/diff.txt
test -f tmp/c3_repro_bundle/bad/meta.json
test -f tmp/c3_repro_bundle/bad/stop_dump.bin

echo "OK c3 repro bundle"
