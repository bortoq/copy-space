#!/bin/sh
set -eu

MANIFEST="third_party/riscv-external/manifest_rv32i_full_strict.json"
[ -f "$MANIFEST" ] || { echo "FAIL: missing $MANIFEST" >&2; exit 1; }

OUT="tmp/rv32_service_external_full"
rm -rf "$OUT"
mkdir -p "$OUT"

python3 scripts/riscv/run_external_rv32i_corpus.py \
  --manifest "$MANIFEST" \
  --outdir "$OUT" \
  --with-vm-run

python3 - <<'PY'
import json
from pathlib import Path
s = json.loads(Path('tmp/rv32_service_external_full/summary.json').read_text(encoding='utf-8'))
if not s.get('ok'):
    raise SystemExit('FAIL: strict full external corpus has failures')
if s.get('waived'):
    raise SystemExit('FAIL: waived cases are not allowed')
if s.get('skipped'):
    raise SystemExit('FAIL: skipped cases are not allowed in strict full gate')
print('OK rv32 service external full strict')
PY
