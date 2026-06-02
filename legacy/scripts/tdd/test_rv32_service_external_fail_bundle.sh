#!/bin/sh
set -eu
# Fail-bundle contract: strict external gate must produce summary artifact.
OUT="tmp/rv32_service_external_full"
sh scripts/tdd/test_rv32_service_external_full_strict.sh >/dev/null
test -f "$OUT/summary.json"
python3 - <<'PY'
import json
from pathlib import Path
p=Path('tmp/rv32_service_external_full/summary.json')
s=json.loads(p.read_text(encoding='utf-8'))
for k in ('ok','ran','failures','skipped','waived'):
    assert k in s, f'missing key: {k}'
print('OK rv32 service external fail bundle')
PY
