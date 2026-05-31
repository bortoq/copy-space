#!/bin/sh
set -eu

mkdir -p tmp

std7="tmp/trace_std7.bin"
tok="tmp/trace_prog.tok"
compiled="tmp/trace_compiled.bin"
trace="tmp/vm_trace.jsonl"

build/bin/mkimage_std7_fixed --out "$std7" >/dev/null 2>tmp/trace_mk.stderr
build/bin/forth0c --image "$std7" --in src/forth0/tests/smoke_include.f0 --out "$tok" >/dev/null 2>tmp/trace_f0c.stderr

build/bin/vmrun --image "$std7" --life 20000000 --dump "$compiled" --trace-jsonl "$trace" \
  < "$tok" >/dev/null 2>tmp/trace_compile.stderr

test -s "$trace"
python3 - "$trace" << 'PY'
import json,sys
p=sys.argv[1]
with open(p,'r',encoding='utf-8') as f:
    lines=[ln.strip() for ln in f if ln.strip()]
assert lines, 'empty trace'
first=json.loads(lines[0])
assert 'tick' in first and 'copies' in first
if first['copies']:
    c=first['copies'][0]
    for k in ('slot','dst','n','src'):
        assert k in c, f'missing {k}'
print('OK vmrun trace jsonl')
PY
