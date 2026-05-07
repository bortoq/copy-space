#!/usr/bin/env python3
# file: scripts/bench/summarize.py
# purpose: summarize benchmark CSV v0 into a human-readable report

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def die(msg: str) -> None:
    raise SystemExit("ERROR: " + msg)


def fnum(x: str) -> float:
    x = (x or "").strip()
    if x == "" or x == "-":
        return float("nan")
    return float(x)


def inum(x: str) -> int:
    x = (x or "").strip()
    if x == "" or x == "-":
        return -1
    return int(x)


@dataclass
class Row:
    schema_version: str
    bench: str
    mode: str
    seed: str
    space_bytes: int
    slots: int
    addr_bits: int
    ticks_total: int
    moved_bits_total: int
    vmrep_avg_bits_sum_per_tick: float
    vmrep_avg_bits_uniq_dst_per_tick: float
    notes: str
    git_rev: str


CSV_V0_COLS = [
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
]


def read_rows(path: Path) -> List[Row]:
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            die("CSV has no header")
        # Accept supersets, but require v0 columns exist
        missing = [c for c in CSV_V0_COLS if c not in r.fieldnames]
        if missing:
            die(f"CSV missing columns: {missing}")

        out: List[Row] = []
        for d in r:
            out.append(
                Row(
                    schema_version=(d.get("schema_version") or "").strip(),
                    bench=(d.get("bench") or "").strip(),
                    mode=(d.get("mode") or "").strip(),
                    seed=(d.get("seed") or "").strip(),
                    space_bytes=inum(d.get("space_bytes") or ""),
                    slots=inum(d.get("slots") or ""),
                    addr_bits=inum(d.get("addr_bits") or ""),
                    ticks_total=inum(d.get("ticks_total") or ""),
                    moved_bits_total=inum(d.get("moved_bits_total") or ""),
                    vmrep_avg_bits_sum_per_tick=fnum(d.get("vmrep_avg_bits_sum_per_tick") or ""),
                    vmrep_avg_bits_uniq_dst_per_tick=fnum(d.get("vmrep_avg_bits_uniq_dst_per_tick") or ""),
                    notes=(d.get("notes") or "").strip(),
                    git_rev=(d.get("git_rev") or "").strip(),
                )
            )
        return out


def key_basic(x: Row) -> Tuple:
    return (x.bench, x.mode, x.space_bytes, x.slots, x.addr_bits)


def fmt_bits_per_tick(v: float) -> str:
    if v != v:  # nan
        return "-"
    # also show bytes/tick
    bpt = v / 8.0
    if bpt >= 1024:
        return f"{v:,.0f} bits/tick ({bpt/1024.0:,.2f} KiB/tick)"
    return f"{v:,.0f} bits/tick ({bpt:,.1f} B/tick)"


def main() -> int:
    ap = argparse.ArgumentParser(description="Summarize benchmark CSV (schema v0).")
    ap.add_argument("--in", dest="inp", required=True, help="input CSV file")
    ap.add_argument("--top", type=int, default=5, help="show top N rows per group (by uniq_dst)")
    args = ap.parse_args()

    path = Path(args.inp)
    rows = read_rows(path)
    if not rows:
        die("no data rows")

    # group
    groups: Dict[Tuple, List[Row]] = defaultdict(list)
    for x in rows:
        groups[key_basic(x)].append(x)

    print(f"# bench summary: {path}")
    print(f"# rows={len(rows)} groups={len(groups)}")
    print()

    # stable order by bench name
    for k in sorted(groups.keys()):
        g = groups[k]
        bench, mode, space_bytes, slots, addr_bits = k

        # sort by uniq dst desc
        g_sorted = sorted(g, key=lambda r: (r.vmrep_avg_bits_uniq_dst_per_tick if r.vmrep_avg_bits_uniq_dst_per_tick == r.vmrep_avg_bits_uniq_dst_per_tick else -1.0), reverse=True)

        best = g_sorted[0]
        print(f"## {bench} mode={mode} space_bytes={space_bytes} slots={slots} addr_bits={addr_bits}")
        print(f"- best uniq_dst: {fmt_bits_per_tick(best.vmrep_avg_bits_uniq_dst_per_tick)}")
        print(f"- best sum:      {fmt_bits_per_tick(best.vmrep_avg_bits_sum_per_tick)}")
        if best.git_rev:
            print(f"- git_rev: {best.git_rev}")
        print()

        n = min(args.top, len(g_sorted))
        print("| rank | uniq_dst avg | sum avg | ticks_total | moved_bits_total | seed | notes | git_rev |")
        print("|---:|---:|---:|---:|---:|---:|---|---|")
        for i in range(n):
            r = g_sorted[i]
            uniq_s = "-" if r.vmrep_avg_bits_uniq_dst_per_tick != r.vmrep_avg_bits_uniq_dst_per_tick else f"{r.vmrep_avg_bits_uniq_dst_per_tick:,.3f}"
            sum_s  = "-" if r.vmrep_avg_bits_sum_per_tick != r.vmrep_avg_bits_sum_per_tick else f"{r.vmrep_avg_bits_sum_per_tick:,.3f}"
            print(
                f"| {i+1} | {uniq_s} | {sum_s} | {r.ticks_total} | {r.moved_bits_total} | {r.seed or '-'} | {r.notes or '-'} | {r.git_rev or '-'} |"
            )
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
