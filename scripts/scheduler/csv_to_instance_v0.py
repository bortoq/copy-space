#!/usr/bin/env python3
import argparse
import csv
import json
import sys

MODEL = "STRICT1"

def eprint(*a):
    print(*a, file=sys.stderr)

def parse_args():
    ap = argparse.ArgumentParser(description="Convert demands CSV (src_slot,dst_slot,bits_total) into Instance v0 JSON")
    ap.add_argument("csv_path")
    ap.add_argument("--out", required=True, help="output instance JSON path")
    ap.add_argument("--bw", type=int, required=True, help="copy_bw_bits_per_tick (>0)")
    ap.add_argument("--slots", type=int, default=None, help="slots count (>0); if omitted, inferred from max slot id + 1")
    ap.add_argument("--id", default=None)
    ap.add_argument("--notes", default=None)
    return ap.parse_args()

def read_demands_csv(path):
    demands = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        # allow both headered and headerless CSV
        sample = f.read(4096)
        f.seek(0)
        has_header = ("src_slot" in sample and "dst_slot" in sample and "bits_total" in sample)
        if has_header:
            rdr = csv.DictReader(f)
            for i, row in enumerate(rdr):
                try:
                    s = int(row["src_slot"])
                    t = int(row["dst_slot"])
                    b = int(row["bits_total"])
                except Exception:
                    raise ValueError(f"bad row {i}: expected src_slot,dst_slot,bits_total integers")
                demands.append((s, t, b))
        else:
            rdr = csv.reader(f)
            for i, row in enumerate(rdr):
                if not row or all(not x.strip() for x in row):
                    continue
                if len(row) < 3:
                    raise ValueError(f"bad row {i}: expected 3 columns (src_slot,dst_slot,bits_total)")
                s = int(row[0]); t = int(row[1]); b = int(row[2])
                demands.append((s, t, b))
    return demands

def main():
    a = parse_args()
    if a.bw <= 0:
        eprint("ERROR: --bw must be > 0")
        return 1

    try:
        rows = read_demands_csv(a.csv_path)
    except Exception as e:
        eprint("ERROR: failed to read CSV:", e)
        return 1

    if not rows:
        eprint("ERROR: no demands found in CSV")
        return 1

    # infer slots if needed
    max_slot = -1
    for s, t, b in rows:
        max_slot = max(max_slot, s, t)
    slots = a.slots if a.slots is not None else (max_slot + 1)
    if slots <= 0:
        eprint("ERROR: slots must be > 0")
        return 1

    # merge duplicates
    dm = {}
    for s, t, b in rows:
        if s < 0 or t < 0 or s >= slots or t >= slots:
            eprint(f"ERROR: slot out of bounds in CSV: {s}->{t} (slots={slots})")
            return 1
        if s == t:
            eprint(f"ERROR: src_slot == dst_slot in CSV: {s}")
            return 1
        if b <= 0:
            eprint(f"ERROR: bits_total must be > 0 in CSV: {s}->{t} bits_total={b}")
            return 1
        dm[(s, t)] = dm.get((s, t), 0) + b

    inst = {
        "version": 0,
        "model": MODEL,
        "slots": slots,
        "copy_bw_bits_per_tick": a.bw,
        "demands": [{"src_slot": s, "dst_slot": t, "bits_total": b} for (s, t), b in sorted(dm.items())],
    }
    if a.id is not None:
        inst["id"] = a.id
    if a.notes is not None:
        inst["notes"] = a.notes

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(inst, f, indent=2, sort_keys=True)
        f.write("\n")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
