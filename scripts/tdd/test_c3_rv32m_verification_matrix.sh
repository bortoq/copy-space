#!/bin/sh
set -eu

# Directed truth gates
sh scripts/tdd/test_c3_m_fastpath.sh
sh scripts/tdd/test_c3_m_mul4.sh
sh scripts/tdd/test_c3_m_div4.sh
sh scripts/tdd/test_c3_m_div_corner.sh

# Differential gates
sh scripts/tdd/test_c3_m_fastpath_trace_diff.sh
sh scripts/tdd/test_c3_m_run_diff.sh
sh scripts/tdd/test_c3_m_mul4_trace_diff.sh
sh scripts/tdd/test_c3_m_mul4_run_diff.sh
sh scripts/tdd/test_c3_m_div4_trace_diff.sh
sh scripts/tdd/test_c3_m_div4_run_diff.sh
sh scripts/tdd/test_c3_m_div_corner_trace_diff.sh
sh scripts/tdd/test_c3_m_div_corner_run_diff.sh

# Repro-bundle on mismatch
sh scripts/tdd/test_c3_m_repro_bundle.sh

mkdir -p tmp
python3 - << 'PY'
import json
from pathlib import Path
obj = {
  "matrix": "rv32m-verification-v1",
  "ok": True,
  "instructions": ["mul", "mulh", "mulhu", "mulhsu", "div", "divu", "rem", "remu"],
  "coverage": {
    "directed_truth": ["m_fastpath", "m_mul4", "m_div4", "m_div_corner"],
    "trace_diff": ["m_fastpath", "m_mul4", "m_div4", "m_div_corner"],
    "run_diff": ["m_fastpath", "m_mul4", "m_div4", "m_div_corner"],
    "repro_bundle": ["m_div4_negative"]
  },
  "artifacts": {
    "mismatch_bundle": "tmp/c3_m_repro/bad"
  }
}
Path('tmp/c3_rv32m_verification_matrix.json').write_text(json.dumps(obj, indent=2) + "\n", encoding='utf-8')
print('OK c3 rv32m verification matrix')
PY
