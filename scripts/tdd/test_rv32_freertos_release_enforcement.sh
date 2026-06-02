#!/bin/sh
set -eu

RUNNER="scripts/tdd/run_rv32_service_release_full.sh"
[ -f "$RUNNER" ] || { echo "FAIL: missing $RUNNER" >&2; exit 1; }

rg -q "test_rv32_freertos_three_binary_interactive_e2e.sh" "$RUNNER"
rg -q "test_rv32_stage20_evidence_bundle.sh" "$RUNNER"

sh scripts/tdd/test_rv32_freertos_three_binary_interactive_e2e.sh >/dev/null
sh scripts/tdd/test_rv32_stage20_evidence_bundle.sh >/dev/null

SUM="tmp/rv32_stage20_evidence/summary.json"
[ -f "$SUM" ] || { echo "FAIL: missing $SUM" >&2; exit 1; }

python3 - <<'PY'
import json
from pathlib import Path
s = json.loads(Path("tmp/rv32_stage20_evidence/summary.json").read_text(encoding="utf-8"))
fr = s.get("freertos", {})
required_top = ["guest_sha256", "command_transcript_hash", "final_snapshot"]
for k in required_top:
    if k not in fr:
        raise SystemExit(f"FAIL: missing freertos.{k}")
fs = fr["final_snapshot"]
for k in ["task_count", "tick_count", "heap_watermark", "rsp"]:
    if k not in fs:
        raise SystemExit(f"FAIL: missing freertos.final_snapshot.{k}")
if fs["task_count"] < 1 or fs["tick_count"] < 1:
    raise SystemExit("FAIL: invalid freertos final snapshot values")
print("OK rv32 freertos release enforcement")
PY
