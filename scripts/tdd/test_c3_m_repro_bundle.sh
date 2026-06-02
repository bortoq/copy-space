#!/bin/sh
set -eu
mkdir -p tmp/c3_m_repro
cat > tmp/c3_m_repro/ref_bad.json << 'JSON'
[
  {"step":0,"mode":"native","guest_pc":0,"instr_name":"div","rd":1,"rd_value":123,"mem_write":null,"stop_reason":null}
]
JSON

if scripts/riscv/c3_run_and_diff.sh --case m_div4 --mode native --ref-trace tmp/c3_m_repro/ref_bad.json --outdir tmp/c3_m_repro/bad >/dev/null 2>&1; then
  echo "FAIL c3 m repro bundle: expected mismatch" >&2
  exit 1
fi

test -f tmp/c3_m_repro/bad/c3_trace.json
test -f tmp/c3_m_repro/bad/ref_trace.json
test -f tmp/c3_m_repro/bad/diff.txt
test -f tmp/c3_m_repro/bad/meta.json
test -f tmp/c3_m_repro/bad/stop_dump.bin

echo "OK c3 m repro bundle"
