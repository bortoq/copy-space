#!/usr/bin/env python3
import argparse
import json
import sys

MODEL = "STRICT1"

def main():
    ap = argparse.ArgumentParser(description="Convert lines: tick src dst len_bits -> Schedule v0 JSON")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("path", help="input text file ('-' for stdin)")
    args = ap.parse_args()

    ticks = {}
    f = sys.stdin if args.path == "-" else open(args.path, "r", encoding="utf-8")
    with f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) != 4:
                raise SystemExit(f"ERROR line {ln}: expected 4 fields: tick src dst len_bits")
            ti, s, t, l = map(int, parts)
            ticks.setdefault(ti, []).append({"src_slot": s, "dst_slot": t, "len_bits": l})

    max_tick = max(ticks.keys(), default=-1)
    out_ticks = []
    for i in range(max_tick + 1):
        out_ticks.append(ticks.get(i, []))

    sched = {"version": 0, "model": args.model, "ticks": out_ticks}
    with open(args.out, "w", encoding="utf-8") as fp:
        json.dump(sched, fp, indent=2, sort_keys=True)
        fp.write("\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
