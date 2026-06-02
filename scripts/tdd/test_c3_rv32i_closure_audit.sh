#!/bin/sh
set -eu

run_gate() {
  name="$1"
  cmd="$2"
  if sh -c "$cmd" >/dev/null; then
    echo "  \"$name\": \"pass\"" >> "$OUT"
  else
    echo "  \"$name\": \"fail\"" >> "$OUT"
    return 1
  fi
}

mkdir -p tmp
OUT="tmp/c3_rv32i_closure_audit.json"
rm -f "$OUT"

{
  echo "{"
  echo "  \"audit\": \"rv32i-closure-v1\"," 
  echo "  \"date\": \"$(date +%Y-%m-%d)\","
  echo "  \"gates\": {"
} > "$OUT"

ok=1

run_gate decode_known_unknown "scripts/tdd/test_c3_decode_known_unknown.sh" || ok=0
run_gate dispatch_matrix "scripts/tdd/test_c3_dispatch_matrix.sh" || ok=0
run_gate branch_matrix "scripts/tdd/test_c3_branch_matrix.sh" || ok=0
run_gate branch_trace_diff "scripts/tdd/test_c3_branch_matrix_trace_diff.sh" || ok=0
run_gate mem_align_fault "scripts/tdd/test_c3_mem_align_fault.sh" || ok=0
run_gate mem_bounds_fault "scripts/tdd/test_c3_mem_bounds_fault.sh" || ok=0
run_gate mem_subword "scripts/tdd/test_c3_mem_subword.sh" || ok=0
run_gate mem_subword_trace_diff "scripts/tdd/test_c3_mem_subword_trace_diff.sh" || ok=0
run_gate stop_contract "scripts/tdd/test_c3_m0_stop_contract.sh" || ok=0
run_gate c2_no_regression "scripts/tdd/test_c3_r6_no_regression.sh" || ok=0

# remove trailing comma on last gate line by rewriting compactly
python3 - <<'PY'
import json
from pathlib import Path
p = Path('tmp/c3_rv32i_closure_audit.json')
lines = p.read_text(encoding='utf-8').splitlines()
# reconstruct from collected pass/fail pairs
pairs = {}
for ln in lines:
    if ln.strip().startswith('"') and ':' in ln:
        k,v = ln.strip().rstrip(',').split(':',1)
        k = k.strip().strip('"')
        v = v.strip().strip('"')
        if k not in ('audit','date','gates'):
            pairs[k]=v
obj = {
  'audit': 'rv32i-closure-v1',
  'date': __import__('datetime').date.today().isoformat(),
  'gates': pairs,
}
obj['status'] = 'pass' if all(v=='pass' for v in pairs.values()) else 'fail'
p.write_text(json.dumps(obj, indent=2)+"\n", encoding='utf-8')
PY

if [ "$ok" -ne 1 ]; then
  echo "FAIL c3 rv32i closure audit" >&2
  exit 1
fi

echo "OK c3 rv32i closure audit"
