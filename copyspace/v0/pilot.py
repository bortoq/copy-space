#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
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

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_instance_from_csv(csv_path: str, bw: int, slots: int | None, inst_id: str | None, notes: str | None) -> dict:
    rows = c2i.read_demands_csv(csv_path)  # list[(src,dst,bits)]
    if not rows:
        raise SystemExit("ERROR: no demands found in CSV")

    max_slot = max(max(s, t) for (s, t, _b) in rows)
    if slots is None:
        slots = max_slot + 1
    if slots <= 0:
        raise SystemExit("ERROR: slots must be > 0")

    dm: dict[tuple[int, int], int] = {}
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

def rep_lb(rep: dict) -> int:
    return int(rep.get("lower_bound_ticks", rep.get("max_degree_chunks", 0)))

def rep_gap_ticks(rep: dict) -> int:
    if "gap_ticks" in rep:
        return int(rep["gap_ticks"])
    return int(rep.get("ticks_total", 0)) - rep_lb(rep)

def rep_gap_ratio(rep: dict) -> float:
    if "gap_to_lower_bound" in rep:
        return float(rep["gap_to_lower_bound"])
    lb = rep_lb(rep)
    gt = rep_gap_ticks(rep)
    return (gt / lb) if lb > 0 else 0.0

def tick_participation_grid(inst: dict, sched: dict, max_ticks: int) -> tuple[list[list[int]], int]:
    slots = int(inst["slots"])
    ticks = sched.get("ticks", []) or []
    T = len(ticks)
    Tshow = min(T, max_ticks)

    # grid[slot][tick] = 0 unused, 1 src, 2 dst
    grid = [[0 for _ in range(Tshow)] for _ in range(slots)]
    for ti in range(Tshow):
        tick = ticks[ti]
        for ch in tick:
            s = int(ch["src_slot"])
            d = int(ch["dst_slot"])
            if 0 <= s < slots:
                grid[s][ti] = 1
            if 0 <= d < slots:
                grid[d][ti] = 2
    return grid, T

def html_heatmap(inst: dict, sched: dict, rep: dict, solver: str, max_ticks: int) -> str:
    grid, T = tick_participation_grid(inst, sched, max_ticks)
    slots = int(inst["slots"])
    Tshow = min(T, max_ticks)

    title = f"Copy-Space pilot plot ({solver})"
    meta = [
        ("status", str(rep.get("status", "?"))),
        ("ticks_total", str(rep.get("ticks_total", "-"))),
        ("lower_bound_ticks", str(rep_lb(rep))),
        ("gap_ticks", str(rep_gap_ticks(rep))),
        ("gap_to_lower_bound", f"{rep_gap_ratio(rep):.6f}"),
        ("utilization", f"{float(rep.get('utilization', 0.0)):.6f}" if "utilization" in rep else "-"),
        ("bits_per_tick", f"{float(rep.get('bits_per_tick', 0.0)):.2f}" if "bits_per_tick" in rep else "-"),
        ("expected_bits_per_tick", str(rep.get("expected_bits_per_tick", "-"))),
    ]

    css = """
    body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 16px; }
    h1 { margin: 0 0 8px 0; font-size: 18px; }
    .note { color: #444; margin: 4px 0 16px 0; }
    table.meta { border-collapse: collapse; margin: 8px 0 16px 0; }
    table.meta td { padding: 4px 8px; border-bottom: 1px solid #eee; }
    table.meta td.k { color: #333; font-weight: 600; }
    .gridwrap { overflow-x: auto; border: 1px solid #eee; padding: 8px; }
    table.grid { border-collapse: collapse; }
    table.grid td { width: 10px; height: 10px; padding: 0; border: 1px solid #f5f5f5; }
    td.u0 { background: #ffffff; }
    td.u1 { background: #4e79a7; }  /* src */
    td.u2 { background: #f28e2b; }  /* dst */
    .legend { margin-top: 8px; font-size: 12px; color: #333; }
    .legend span { display: inline-block; padding: 2px 8px; margin-right: 8px; border: 1px solid #eee; }
    .src { background: #4e79a7; color: #fff; }
    .dst { background: #f28e2b; color: #fff; }
    """

    out = []
    out.append("<!doctype html>")
    out.append("<html><head><meta charset='utf-8'>")
    out.append("<meta name='viewport' content='width=device-width, initial-scale=1'>")
    out.append(f"<title>{html.escape(title)}</title>")
    out.append(f"<style>{css}</style></head><body>")
    out.append(f"<h1>{html.escape(title)}</h1>")
    if T > Tshow:
        out.append(f"<div class='note'>Note: showing first {Tshow} ticks out of {T} total.</div>")
    else:
        out.append(f"<div class='note'>Showing {Tshow} ticks.</div>")

    out.append("<table class='meta'>")
    for k, v in meta:
        out.append("<tr>")
        out.append(f"<td class='k'>{html.escape(k)}</td>")
        out.append(f"<td>{html.escape(v)}</td>")
        out.append("</tr>")
    out.append("</table>")

    out.append("<div class='gridwrap'>")
    out.append("<table class='grid'>")
    # rows: slots
    for si in range(slots):
        out.append("<tr>")
        row = grid[si]
        for ti in range(Tshow):
            out.append(f"<td class='u{row[ti]}' title='slot {si}, tick {ti}'></td>")
        out.append("</tr>")
    out.append("</table>")
    out.append("</div>")

    out.append("<div class='legend'>Legend: ")
    out.append("<span class='src'>src</span>")
    out.append("<span class='dst'>dst</span>")
    out.append("</div>")

    out.append("</body></html>")
    out.append("")
    return "\n".join(out)

def write_plot_html(outdir: str, inst: dict, solver: str, sched: dict, rep: dict, max_ticks: int) -> str:
    name = f"plot_{solver}.html"
    path = os.path.join(outdir, name)
    html_s = html_heatmap(inst, sched, rep, solver, max_ticks)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_s)
    return path

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="One-command pilot run (CSV -> instance -> schedules -> reports).")
    ap.add_argument("--csv", required=True, help="demands CSV (src_slot,dst_slot,bits_total)")
    ap.add_argument("--bw", required=True, type=int, help="copy_bw_bits_per_tick (>0)")
    ap.add_argument("--slots", type=int, default=None, help="slots count (optional; inferred if omitted)")
    ap.add_argument("--outdir", default="tmp/pilot", help="output directory")
    ap.add_argument("--id", default=None)
    ap.add_argument("--notes", default=None)
    ap.add_argument("--plot", action="store_true", help="write HTML plots to outdir (no extra deps)")
    ap.add_argument("--plot-max-ticks", type=int, default=256, help="max ticks to render in plots")
    args = ap.parse_args(argv)

    if args.bw <= 0:
        raise SystemExit("ERROR: --bw must be > 0")
    if not os.path.isfile(args.csv):
        raise SystemExit(f"ERROR: missing CSV file: {args.csv}")
    if args.plot_max_ticks <= 0:
        raise SystemExit("ERROR: --plot-max-ticks must be > 0")

    outdir = args.outdir
    Path(outdir).mkdir(parents=True, exist_ok=True)

    inst = build_instance_from_csv(args.csv, args.bw, args.slots, args.id, args.notes)
    dump_json(os.path.join(outdir, "instance.json"), inst)

    schedules: dict[str, dict] = {}
    reports: dict[str, dict] = {}

    for solver in ("baseline", "greedy"):
        sched, rep = solve_and_validate(inst, solver)
        schedules[solver] = sched
        reports[solver] = rep
        dump_json(os.path.join(outdir, f"schedule_{solver}.json"), sched)
        dump_json(os.path.join(outdir, f"report_{solver}.json"), rep)

    def line(name: str, r: dict) -> None:
        util = float(r.get("utilization", 0.0))
        bpt = float(r.get("bits_per_tick", 0.0))
        lb = rep_lb(r)
        gap = rep_gap_ticks(r)
        gapr = rep_gap_ratio(r)
        print(
            f"{name:8s} status={r.get('status')} ticks={r.get('ticks_total')} "
            f"lb={lb} gap={gap} gapr={gapr:.6f} util={util:.4f} bpt={bpt:.2f}"
        )

    b = reports["baseline"]
    g = reports["greedy"]

    line("baseline", b)
    line("greedy", g)
    if b.get("status") == "PASS" and g.get("status") == "PASS":
        print("delta_ticks_total:", int(b["ticks_total"]) - int(g["ticks_total"]))
        print("delta_gap_ticks:", rep_gap_ticks(b) - rep_gap_ticks(g))

    plot_paths = []
    if args.plot:
        for solver in ("baseline", "greedy"):
            pth = write_plot_html(outdir, inst, solver, schedules[solver], reports[solver], args.plot_max_ticks)
            plot_paths.append(pth)
        for pth in plot_paths:
            print("[pilot] wrote plot:", pth)

    print(f"[pilot] wrote artifacts to: {outdir}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
