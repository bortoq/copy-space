#!/bin/sh
set -eu

mkdir -p tmp/c3_schema
python3 scripts/riscv/c3_emit_trace.py --case mvp5 --mode native --trace-mode full --out tmp/c3_schema/full.json >/dev/null
python3 scripts/riscv/c3_emit_trace.py --case mvp5 --mode native --trace-mode compact --out tmp/c3_schema/compact.json >/dev/null

python3 - <<'PY'
import json
from pathlib import Path

full = json.loads(Path('tmp/c3_schema/full.json').read_text(encoding='utf-8'))
compact = json.loads(Path('tmp/c3_schema/compact.json').read_text(encoding='utf-8'))
assert isinstance(full, list) and full
assert isinstance(compact, list) and compact
req_full = {'step','mode','guest_pc','instr_name','rd','rd_value','mem_write','stop_reason'}
req_compact = {'step','guest_pc','instr_name','rd','rd_value','mem_write','stop_reason'}
for i, s in enumerate(full):
    assert req_full.issubset(s.keys()), ("full", i, sorted(s.keys()))
for i, s in enumerate(compact):
    assert req_compact.issubset(s.keys()), ("compact", i, sorted(s.keys()))
    assert 'mode' not in s, ("compact_has_mode", i)
print('OK c3 trace schema full+compact')
PY
