#!/bin/sh
set -eu

# Strict black-box style gate for local external corpus.
# Requirements:
# - local-only artifacts under third_party/riscv-external
# - vm-level execution enabled (no --skip-vm-run)
# - deterministic summary across two runs

MANIFEST="third_party/riscv-external/manifest_rv32i.json"
[ -f "$MANIFEST" ] || { echo "FAIL: missing manifest $MANIFEST" >&2; exit 1; }

OUT1="tmp/rv32_service_blackbox/run1"
OUT2="tmp/rv32_service_blackbox/run2"
rm -rf "$OUT1" "$OUT2"
mkdir -p "$OUT1" "$OUT2"

python3 scripts/riscv/run_external_rv32i_corpus.py \
  --manifest "$MANIFEST" \
  --outdir "$OUT1" \
  --with-vm-run \
  --allow-failures-file doc/rv32_service_skip_policy.json

python3 scripts/riscv/run_external_rv32i_corpus.py \
  --manifest "$MANIFEST" \
  --outdir "$OUT2" \
  --with-vm-run \
  --allow-failures-file doc/rv32_service_skip_policy.json

python3 - <<'PY'
import json
from pathlib import Path

s1 = json.loads(Path('tmp/rv32_service_blackbox/run1/summary.json').read_text(encoding='utf-8'))
s2 = json.loads(Path('tmp/rv32_service_blackbox/run2/summary.json').read_text(encoding='utf-8'))

if not s1.get('ok') or not s2.get('ok'):
    raise SystemExit('FAIL: blackbox summary reports failure')
if s1.get('ran', 0) <= 0:
    raise SystemExit('FAIL: no external cases were executed')

# Determinism for strict gate: same ran/skipped/failures shape across runs.
for k in ('ran',):
    if s1.get(k) != s2.get(k):
        raise SystemExit(f'FAIL: nondeterministic {k}: {s1.get(k)} vs {s2.get(k)}')

if len(s1.get('failures', [])) != len(s2.get('failures', [])):
    raise SystemExit('FAIL: nondeterministic failure count')
if len(s1.get('skipped', [])) != len(s2.get('skipped', [])):
    raise SystemExit('FAIL: nondeterministic skipped count')
if len(s1.get('waived', [])) != len(s2.get('waived', [])):
    raise SystemExit('FAIL: nondeterministic waived count')
if s1.get('waived') or s2.get('waived'):
    raise SystemExit('FAIL: zero-waiver mode violated')
if s1.get('failures') or s2.get('failures'):
    raise SystemExit('FAIL: failures present in strict blackbox gate')

print('OK rv32 service external blackbox deterministic')
PY

echo "OK rv32 service external channel blackbox"
