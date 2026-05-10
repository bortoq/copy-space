#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from copyspace.v0 import csv_to_instance as c2i
from copyspace.v0 import solve as sol
from copyspace.v0 import validate as val

MODEL = "STRICT1"

def dump_json(path: str, obj: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")

def build_instance_from_csv(csv_path: str, bw: int, slots: int | None, inst_id: str | None, notes: str | None) -> dict:
    rows = c2i.read_demands_csv(csv_path)  # list[(src,dst,bits)]
    if not rows:
        raise SystemExit("ERROR: no demands found in CSV")

    max_slot = max(max(s, t) for (s, t, _b) in rows)
    if slots is None:
        slots = max_slot + 1
    if slots <= 0:
        raise SystemExit("ERROR: slots must be > 0")

    dm: dict[tuple[int,int], int] = {}
    for (s, t, b) in rows:
        if s < 0 or t < 0 or s >= slots or t >= slots:
            raise SystemExit(f"ERROR: slot out of bounds in CSV: {s}->{t} (slots={slots})")
        if s == t:
            raise SystemExit(f"ERROR: src_slot == dst_slot in CSV: {s}")
        if b <= 0:
            raise SystemExit(f"ERROR: bits_total must be > 0 in CSV: {s}->{t} bits_total={b}")
        dm[(s, t)] = dm.get((s, t), 0) + b

    inst = {
        "version": 0,
        "model": MODEL,
        "slots": slots,
        "copy_bw_bits_per_tick": bw,
        "demands": [{"src_slot": s, "dst_slot": t, "bits_total": b} for (s, t), b in sorted(dm.items())],
    }
    if inst_id is not None:
        inst["id"] = inst_id
    if notes is not None:
        inst["notes"] = notes
    return inst

def solve_and_validate(inst: dict, solver: str) -> tuple[dict, dict]:
    bw = int(inst["copy_bw_bits_per_tick"])
    demands = inst.get("demands", [])
    pending = sol.chunk_demands(demands, bw)

    if solver == "baseline":
        ticks = sol.solve_baseline_strict1(pending)
    elif solver == "greedy":
        ticks = sol.solve_greedy_strict1(pending)
    else:
        raise SystemExit(f"ERROR: unknown solver: {solver}")

    sched = {"version": 0, "model": MODEL, "ticks": ticks}
    rep = val.validate_core_v0(inst, sched)
    return sched, rep

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="One-command pilot run (CSV -> instance -> schedules -> reports).")
    ap.add_argument("--csv", required=True, help="demands CSV (src_slot,dst_slot,bits_total)")
    ap.add_argument("--bw", required=True, type=int, help="copy_bw_bits_per_tick (>0)")
    ap.add_argument("--slots", type=int, default=None, help="slots count (optional; inferred if omitted)")
    ap.add_argument("--outdir", default="tmp/pilot", help="output directory")
    ap.add_argument("--id", default=None)
    ap.add_argument("--notes", default=None)
    args = ap.parse_args(argv)

    if args.bw <= 0:
        raise SystemExit("ERROR: --bw must be > 0")
    if not os.path.isfile(args.csv):
        raise SystemExit(f"ERROR: missing CSV file: {args.csv}")

    outdir = args.outdir
    Path(outdir).mkdir(parents=True, exist_ok=True)

    inst = build_instance_from_csv(args.csv, args.bw, args.slots, args.id, args.notes)
    dump_json(os.path.join(outdir, "instance.json"), inst)

    for solver in ("baseline", "greedy"):
        sched, rep = solve_and_validate(inst, solver)
        dump_json(os.path.join(outdir, f"schedule_{solver}.json"), sched)
        dump_json(os.path.join(outdir, f"report_{solver}.json"), rep)

    with open(os.path.join(outdir, "report_baseline.json"), "r", encoding="utf-8") as f:
        b = json.load(f)
    with open(os.path.join(outdir, "report_greedy.json"), "r", encoding="utf-8") as f:
        g = json.load(f)

    def line(name, r):
        util = float(r.get("utilization", 0.0))
        bpt = float(r.get("bits_per_tick", 0.0))
        print(f"{name:8s} status={r.get('status')} ticks={r.get('ticks_total')} util={util:.4f} bpt={bpt:.2f} lb={r.get('max_degree_chunks',0)}")

    line("baseline", b)
    line("greedy", g)
    if b.get("status") == "PASS" and g.get("status") == "PASS":
        print("delta_ticks_total:", int(b["ticks_total"]) - int(g["ticks_total"]))

    print(f"[pilot] wrote artifacts to: {outdir}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
