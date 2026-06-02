#!/bin/sh
set -eu

OUT="tmp/rv32_stage20_evidence"
rm -rf "$OUT"
mkdir -p "$OUT"

# Run executable gates and persist logs as evidence inputs.
sh scripts/tdd/test_rv32_runtime_abi_ops.sh >"$OUT/runtime_abi_ops.log" 2>&1
sh scripts/tdd/test_rv32_guest_lifecycle_contract.sh >"$OUT/guest_lifecycle.log" 2>&1
sh scripts/tdd/test_rv32_guest_run_contract.sh >"$OUT/guest_run.log" 2>&1
sh scripts/tdd/test_rv32_three_binary_ab_diff.sh >"$OUT/three_binary_ab_diff.log" 2>&1
sh scripts/tdd/test_rv32_sha_profile_semantics.sh >"$OUT/sha_profile_semantics.log" 2>&1
sh scripts/tdd/test_rv32_sha256_three_binary_e2e.sh >"$OUT/sha256_three_binary.log" 2>&1
sh scripts/tdd/test_rv32_freertos_channel_io_e2e.sh >"$OUT/freertos_channel_io.log" 2>&1
sh scripts/tdd/test_rv32_c3_run_shortcuts_inventory.sh >"$OUT/c3_run_shortcuts_inventory.log" 2>&1
sh scripts/tdd/test_rv32_c3_unsupported_trap_contract.sh >"$OUT/c3_unsupported_trap_contract.log" 2>&1

# Build deterministic digest map for bundle reproducibility checks.
sha256sum \
  "$OUT/runtime_abi_ops.log" \
  "$OUT/guest_lifecycle.log" \
  "$OUT/guest_run.log" \
  "$OUT/three_binary_ab_diff.log" \
  "$OUT/sha_profile_semantics.log" \
  "$OUT/sha256_three_binary.log" \
  "$OUT/freertos_channel_io.log" \
  "$OUT/c3_run_shortcuts_inventory.log" \
  "$OUT/c3_unsupported_trap_contract.log" \
  > "$OUT/checksums.sha256"

python3 - <<'PY'
import json
import hashlib
from pathlib import Path

out = Path("tmp/rv32_stage20_evidence")
logs = {
    "runtime_abi_ops": (out / "runtime_abi_ops.log").read_text(encoding="utf-8"),
    "guest_lifecycle": (out / "guest_lifecycle.log").read_text(encoding="utf-8"),
    "guest_run": (out / "guest_run.log").read_text(encoding="utf-8"),
    "three_binary_ab_diff": (out / "three_binary_ab_diff.log").read_text(encoding="utf-8"),
    "sha_profile_semantics": (out / "sha_profile_semantics.log").read_text(encoding="utf-8"),
    "sha256_three_binary": (out / "sha256_three_binary.log").read_text(encoding="utf-8"),
    "freertos_channel_io": (out / "freertos_channel_io.log").read_text(encoding="utf-8"),
    "c3_run_shortcuts_inventory": (out / "c3_run_shortcuts_inventory.log").read_text(encoding="utf-8"),
    "c3_unsupported_trap_contract": (out / "c3_unsupported_trap_contract.log").read_text(encoding="utf-8"),
}
for k, v in logs.items():
    if "OK" not in v:
        raise SystemExit(f"FAIL: missing OK marker in {k}")

sha_summary = json.loads(Path("tmp/rv32_sha3bin_last/summary.json").read_text(encoding="utf-8"))
freertos_summary = json.loads(Path("tmp/rv32_freertos_last/summary.json").read_text(encoding="utf-8"))
replay_hash = hashlib.sha256((logs["sha256_three_binary"] + logs["sha_profile_semantics"] + logs["guest_run"]).encode("utf-8")).hexdigest()

gate_manifest = [
    "test_rv32_runtime_abi_ops.sh",
    "test_rv32_guest_lifecycle_contract.sh",
    "test_rv32_guest_run_contract.sh",
    "test_rv32_three_binary_ab_diff.sh",
    "test_rv32_sha_profile_semantics.sh",
    "test_rv32_sha256_three_binary_e2e.sh",
    "test_rv32_freertos_channel_io_e2e.sh",
    "test_rv32_c3_run_shortcuts_inventory.sh",
    "test_rv32_c3_unsupported_trap_contract.sh",
]

bundle = {
    "ok": True,
    "format": "rv32_stage20_evidence_v4",
    "inputs": {
        "guest_binary": sha_summary["guest_binary"],
        "guest_sha256": sha_summary["guest_sha256"],
    },
    "ops_transcript": [
        "LOAD_CODE",
        "RUN",
        "STEP",
        "READ_MEM",
        "STATUS",
    ],
    "final_state": {
        "observed_digest_hex": sha_summary["observed_digest_hex"],
    },
    "digest_assert": {
        "match": bool(sha_summary.get("ok", False)),
    },
    "freertos": {
        "guest_sha256": freertos_summary["guest_sha256"],
        "command_transcript_hash": freertos_summary["command_transcript_hash"],
        "final_snapshot": freertos_summary["final_snapshot"],
    },
    "semantic_gate_verdicts": {
        "runtime_abi_ops": "OK" if "OK" in logs["runtime_abi_ops"] else "FAIL",
        "guest_run": "OK" if "OK" in logs["guest_run"] else "FAIL",
        "sha_profile_semantics": "OK" if "OK" in logs["sha_profile_semantics"] else "FAIL",
        "three_binary_ab_diff": "OK" if "OK" in logs["three_binary_ab_diff"] else "FAIL",
    },
    "determinism_replay_hash": replay_hash,
    "gate_manifest": gate_manifest,
    "artifacts": {
        "runtime_abi_ops_log": str(out / "runtime_abi_ops.log"),
        "guest_lifecycle_log": str(out / "guest_lifecycle.log"),
        "guest_run_log": str(out / "guest_run.log"),
        "three_binary_ab_diff_log": str(out / "three_binary_ab_diff.log"),
        "sha_profile_semantics_log": str(out / "sha_profile_semantics.log"),
        "sha256_three_binary_log": str(out / "sha256_three_binary.log"),
        "freertos_channel_io_log": str(out / "freertos_channel_io.log"),
        "c3_run_shortcuts_inventory_log": str(out / "c3_run_shortcuts_inventory.log"),
        "c3_unsupported_trap_contract_log": str(out / "c3_unsupported_trap_contract.log"),
        "checksums": str(out / "checksums.sha256"),
        "sha256_summary": "tmp/rv32_sha3bin_last/summary.json",
        "freertos_summary": "tmp/rv32_freertos_last/summary.json",
    },
}
(out / "sha256_summary.json").write_text(json.dumps(sha_summary, indent=2) + "\n", encoding="utf-8")
(out / "summary.json").write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
print("OK rv32 stage20 evidence bundle")
PY
