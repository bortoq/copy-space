#!/bin/sh
set -eu

mkdir -p tmp

scripts/riscv/rv32i_mvp_check.py \
  --outdir tmp/rv32i_mvp_demo \
  --max-instr 64 \
  --max-f0-lines 4000 \
  --require addi \
  --require add \
  --require sw >/dev/null

test -f tmp/rv32i_mvp_demo/program.f0
test -f tmp/rv32i_mvp_demo/trace.json
test -f tmp/rv32i_mvp_demo/summary.json

python3 - << 'PY'
import json
s = json.load(open('tmp/rv32i_mvp_demo/summary.json', 'r', encoding='utf-8'))
assert s['ok'] is True
assert s['trace_len'] >= 3
assert 'addi' in s['instructions']
assert 'add' in s['instructions']
assert 'sw' in s['instructions']
print('OK summary checks')
PY
