#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_todoC_vmrep_to_csv"
mkdir -p "$bakdir"

F="scripts/vmrep_to_csv.py"
if [ -f "$F" ]; then
  cp -a "$F" "$bakdir/vmrep_to_csv.py.bak"
fi

cat >"$F" <<'EOF'
#!/usr/bin/env python3
# file: scripts/vmrep_to_csv.py
# date: 2026-05-05
# purpose: extract vmrep metrics from a log and print one CSV row (unified schema v1)

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


KEY_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b\s*[:= ]\s*([0-9]+(?:\.[0-9]+)?)\b")


def die(msg: str, code: int = 1) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(code)


def extract_vmrep_block(text: str) -> str:
    # take the last vmrep block, in case there are multiple runs
    starts = [m.start() for m in re.finditer(r"^\[vmrep\]\s*$", text, flags=re.M)]
    if not starts:
        die("cannot find '[vmrep]' block in log")
    start = starts[-1]
    end_m = re.search(r"^VMREP_END\s*$", text[start:], flags=re.M)
    if not end_m:
        die("cannot find 'VMREP_END' after last [vmrep] in log")
    end = start + end_m.end()
    return text[start:end]


def parse_kv(block: str) -> dict[str, str]:
    kv: dict[str, str] = {}
    for line in block.splitlines():
        m = KEY_RE.search(line)
        if not m:
            continue
        k, v = m.group(1), m.group(2)
        kv[k] = v
    return kv


def pick(kv: dict[str, str], *names: str) -> str:
    for n in names:
        if n in kv:
            return kv[n]
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert vmrep block in a log to one CSV row (schema v1).")
    ap.add_argument("--log", default="tmp/run.log", help="Path to log containing [vmrep]..VMREP_END (default: tmp/run.log)")
    ap.add_argument("--bench", required=True, help="bench name (e.g. pack/permute/bulkcopy)")
    ap.add_argument("--mode", default="", help="mode string (optional)")
    ap.add_argument("--seed", default="", help="seed (optional)")
    ap.add_argument("--space-bytes", default="524288", help="space_bytes (default: 524288)")
    ap.add_argument("--processor-n", default="64", help="processor_n (default: 64)")
    ap.add_argument("--addr-bits", default="24", help="addr_bits (default: 24)")
    ap.add_argument("--moved-bits-total", default="", help="semantic moved bits (optional; leave empty if unknown)")
    ap.add_argument("--notes", default="", help="notes (optional)")
    ap.add_argument("--row-only", action="store_true", help="print only row (no header)")
    args = ap.parse_args()

    log_path = Path(args.log)
    if not log_path.exists():
        die(f"missing log: {log_path}")

    text = log_path.read_text(encoding="utf-8", errors="replace")
    block = extract_vmrep_block(text)
    kv = parse_kv(block)

    # Names here are tolerant: if your vmrep uses slightly different keys, add aliases.
    ticks_total = pick(kv, "ticks_total", "ticks")
    bits_sum_total = pick(kv, "bits_sum_total", "sum_bits_total")
    bits_uniq_total = pick(kv, "bits_uniq_dst_total", "uniq_dst_bits_total", "uniq_bits_total")
    avg_sum = pick(kv, "avg_bits_sum_per_tick", "avg_sum_bits_per_tick")
    avg_uniq = pick(kv, "avg_bits_uniq_dst_per_tick", "avg_uniq_dst_bits_per_tick", "avg_uniq_bits_per_tick")

    thr_from = pick(kv, "thr_from", "window_from", "from")
    thr_len = pick(kv, "thr_len", "window_len", "len")
    thr_avg_sum = pick(kv, "thr_avg_bits_sum_per_tick", "thr_avg_sum_bits_per_tick")
    thr_avg_uniq = pick(kv, "thr_avg_bits_uniq_dst_per_tick", "thr_avg_uniq_dst_bits_per_tick", "thr_avg_uniq_bits_per_tick")

    header = [
        "schema_version",
        "bench", "mode", "seed",
        "space_bytes", "processor_n", "addr_bits",
        "ticks_total",
        "moved_bits_total",
        "vmrep_bits_sum_total",
        "vmrep_bits_uniq_dst_total",
        "vmrep_avg_bits_sum_per_tick",
        "vmrep_avg_bits_uniq_dst_per_tick",
        "thr_from", "thr_len",
        "thr_avg_bits_sum_per_tick",
        "thr_avg_bits_uniq_dst_per_tick",
        "notes",
    ]

    row = [
        "1",
        args.bench, args.mode, args.seed,
        str(args.space_bytes), str(args.processor_n), str(args.addr_bits),
        ticks_total,
        args.moved_bits_total,
        bits_sum_total,
        bits_uniq_total,
        avg_sum,
        avg_uniq,
        thr_from,
        thr_len,
        thr_avg_sum,
        thr_avg_uniq,
        args.notes,
    ]

    w = csv.writer(sys.stdout, lineterminator="\n")
    if not args.row_only:
        w.writerow(header)
    w.writerow(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
EOF

chmod +x "$F"
echo "OK: wrote $F (backup in $bakdir if existed)" >&2
echo "Usage example after running a bench:" >&2
echo "  python3 scripts/vmrep_to_csv.py --bench pack --mode stride --seed 1 --log tmp/run.log" >&2
