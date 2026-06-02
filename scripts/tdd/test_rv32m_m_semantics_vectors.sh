#!/bin/sh
set -eu

python3 scripts/riscv/rv32m_semantics_vectors.py >/dev/null

python3 - <<'PY'
import json
from pathlib import Path

p = Path('tmp/rv32m_vectors.json')
obj = json.loads(p.read_text(encoding='utf-8'))
assert obj['contract'] == 'rv32m-v1'
cases = obj['cases']
assert len(cases) >= 8
req = {'a','b','mul','mulh','mulhu','mulhsu','div','divu','rem','remu'}
for i, c in enumerate(cases):
    assert req.issubset(c.keys()), (i, c.keys())

# critical corner checks
zero_div = [c for c in cases if c['b'] == 0]
assert zero_div, 'missing divisor=0 case'
for c in zero_div:
    assert c['div'] == 0xFFFFFFFF
    assert c['divu'] == 0xFFFFFFFF
    assert c['rem'] == c['a']
    assert c['remu'] == c['a']

ovf = [c for c in cases if c['a'] == 0x80000000 and c['b'] == 0xFFFFFFFF]
assert ovf, 'missing INT_MIN/-1 case'
c = ovf[0]
assert c['div'] == 0x80000000
assert c['rem'] == 0

print('OK rv32m m-semantics vectors')
PY
