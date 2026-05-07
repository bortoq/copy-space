#!/usr/bin/env python3
# file: scripts/vmrep_to_csv.py
# purpose: extract vmrep metrics from a log and print CSV (schema v0, append-only)
#
# Columns (schema v0; append-only):
#   schema_version,bench,mode,seed,space_bytes,slots,addr_bits,
#   ticks_total,moved_bits_total,
#   vmrep_bits_sum_total,vmrep_bits_uniq_dst_total,
#   vmrep_avg_bits_sum_per_tick,vmrep_avg_bits_uniq_dst_per_tick,
#   thr_from,thr_len,thr_avg_bits_sum_per_tick,thr_avg_bits_uniq_dst_per_tick,
#   notes,git_rev,
#   copies_total,expected_bits_per_tick
#
# Notes:
# - `slots` is the CSV name for what the code/tools often call `processor_n`.
# - New columns must be appended at the end.

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from typing import Dict, Optional


COLS = [
    "schema_version",
    "bench",
    "mode",
    "seed",
    "space_bytes",
    "slots",
    "addr_bits",
    "ticks_total",
    "moved_bits_total",
    "vmrep_bits_sum_total",
    "vmrep_bits_uniq_dst_total",
    "vmrep_avg_bits_sum_per_tick",
    "vmrep_avg_bits_uniq_dst_per_tick",
    "thr_from",
    "thr_len",
    "thr_avg_bits_sum_per_tick",
    "thr_avg_bits_uniq_dst_per_tick",
    "notes",
    "git_rev",
    # appended metrics (v0 extension; non-breaking)
    "copies_total",
    "expected_bits_per_tick",
]


def die(msg: str) -> None:
    raise SystemExit("ERROR: " + msg)


def csv_escape(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    if any(c in s for c in [",", '"', "\n", "\r"]):
        s = s.replace('"', '""')
        return f'"{s}"'
    return s


def extract_vmrep_block(text: str) -> str:
    lines = text.splitlines()
    end_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if "VMREP_END" in lines[i]:
            end_idx = i
            break
    if end_idx is None:
        die("cannot find VMREP_END in log")

    start_idx = end_idx
    while start_idx > 0 and lines[start_idx - 1].lstrip().startswith("[vmrep]"):
        start_idx -= 1

    if not lines[start_idx].lstrip().startswith("[vmrep]"):
        die("cannot find '[vmrep]' prefix before VMREP_END")

    return "\n".join(lines[start_idx : end_idx + 1])


def parse_vmrep_kv(block: str) -> Dict[str, str]:
    kv: Dict[str, str] = {}
    for raw in block.splitlines():
        s = raw.strip()
        if not s.startswith("[vmrep]"):
            continue
        s = s[len("[vmrep]") :].strip()
        if not s:
            continue

        parts = s.split()
        for p in parts:
            if "=" not in p:
                continue
            k, v = p.split("=", 1)
            kv[k.strip()] = v.strip()
    return kv


def find_int(text: str, pat: str) -> Optional[int]:
    m = re.search(pat, text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def get_git_rev() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8", errors="strict").strip()
    except Exception:
        return ""


def header_line() -> str:
    return ",".join(COLS)


def row_line(row: Dict[str, str]) -> str:
    return ",".join(csv_escape(row.get(c, "")) for c in COLS)


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert vmrep block in a log to one CSV row (schema v0).")
    ap.add_argument("--log", default="tmp/run.log", help="Path to log containing [vmrep]..VMREP_END")
    ap.add_argument("--bench", default="", help="bench name (pack/permute/bulkcopy/...)")
    ap.add_argument("--mode", default="", help="mode string")
    ap.add_argument("--seed", default="", help="seed (or empty)")
    ap.add_argument("--notes", default="", help="notes string")
    ap.add_argument("--schema-version", default="csv.v0", help="schema version field")
    ap.add_argument("--row-only", action="store_true", help="print only a CSV row (no header)")
    ap.add_argument("--header", action="store_true", help="print only the CSV header and exit")

    # optional appended metrics (preferred to be provided by bench wrappers)
    ap.add_argument("--copies-total", default="", help="total number of copies/edges (optional)")
    ap.add_argument("--expected-bits-per-tick", default="", help="expected bits per tick (optional)")

    args = ap.parse_args()

    if args.header:
        print(header_line())
        return 0

    try:
        text = open(args.log, "r", encoding="utf-8", errors="replace").read()
    except OSError as e:
        die(f"cannot read log '{args.log}': {e}")

    block = extract_vmrep_block(text)
    kv = parse_vmrep_kv(block)

    # best-effort context from log text
    space_bytes = find_int(text, r"\bspace_bytes=(\d+)\b")
    processor_n = find_int(text, r"\bprocessor_n=(\d+)\b")  # exported as 'slots'
    addr_bits = find_int(text, r"\baddr_bits=(\d+)\b")

    ticks_total = kv.get("ticks_total", "")
    bits_sum_total = kv.get("bits_sum_total", "")
    bits_uniq_dst_total = kv.get("bits_uniq_dst_total", "")
    avg_bits_sum_per_tick = kv.get("avg_bits_sum_per_tick", "")
    avg_bits_uniq_dst_per_tick = kv.get("avg_bits_uniq_dst_per_tick", "")

    thr_from = kv.get("thr_from", "")
    thr_len = kv.get("thr_len", "")
    thr_avg_bits_sum_per_tick = kv.get("thr_avg_bits_sum_per_tick", "")
    thr_avg_bits_uniq_dst_per_tick = kv.get("thr_avg_bits_uniq_dst_per_tick", "")

    moved_bits_total = kv.get("moved_bits_total", "") or bits_sum_total

    row: Dict[str, str] = {}
    row["schema_version"] = args.schema_version
    row["bench"] = args.bench
    row["mode"] = args.mode
    row["seed"] = args.seed
    row["space_bytes"] = "" if space_bytes is None else str(space_bytes)
    row["slots"] = "" if processor_n is None else str(processor_n)
    row["addr_bits"] = "" if addr_bits is None else str(addr_bits)

    row["ticks_total"] = ticks_total
    row["moved_bits_total"] = moved_bits_total

    row["vmrep_bits_sum_total"] = bits_sum_total
    row["vmrep_bits_uniq_dst_total"] = bits_uniq_dst_total
    row["vmrep_avg_bits_sum_per_tick"] = avg_bits_sum_per_tick
    row["vmrep_avg_bits_uniq_dst_per_tick"] = avg_bits_uniq_dst_per_tick

    row["thr_from"] = thr_from
    row["thr_len"] = thr_len
    row["thr_avg_bits_sum_per_tick"] = thr_avg_bits_sum_per_tick
    row["thr_avg_bits_uniq_dst_per_tick"] = thr_avg_bits_uniq_dst_per_tick

    row["notes"] = args.notes
    row["git_rev"] = os.environ.get("GIT_REV", "") or get_git_rev()

    # appended metrics
    row["copies_total"] = args.copies_total
    row["expected_bits_per_tick"] = args.expected_bits_per_tick

    if args.row_only:
        print(row_line(row))
    else:
        print(header_line())
        print(row_line(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
