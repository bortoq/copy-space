#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import subprocess
from pathlib import Path
from typing import Dict, Tuple, List

def run_ref_pack_csv(out_csv: str) -> None:
    Path("tmp").mkdir(exist_ok=True)
    subprocess.check_call([
        "scripts/bench/run.sh",
        "--bench", "scheduler",
        "--out", out_csv,
        "--inst-glob", "scripts/scheduler/tests/ref_pack/*.json",
        "--solver-list", "baseline", "greedy",
        "--repeat", "1",
    ])

def parse_solver(notes: str) -> str:
    m = re.search(r"\bsolver=([a-zA-Z0-9_+-]+)\b", notes or "")
    return m.group(1) if m else "unknown"

def main() -> int:
    ap = argparse.ArgumentParser(description="Plot scheduler ref_pack results from unified CSV v0.")
    ap.add_argument("--in", dest="inp", default="tmp/sched_pack.csv", help="input CSV (default: tmp/sched_pack.csv)")
    ap.add_argument("--outdir", default="tmp/plots", help="output directory (default: tmp/plots)")
    ap.add_argument("--run", action="store_true", help="generate CSV from ref_pack first")
    args = ap.parse_args()

    if args.run:
        run_ref_pack_csv(args.inp)

    try:
        import matplotlib.pyplot as plt
    except Exception as e:
        raise SystemExit(f"ERROR: matplotlib not available ({e}). Install: python -m pip install matplotlib")

    inp = Path(args.inp)
    if not inp.exists():
        raise SystemExit(f"ERROR: CSV not found: {inp} (use --run)")

    # (mode, solver) -> (ticks_total, utilization)
    data: Dict[Tuple[str, str], Tuple[int, float]] = {}

    with inp.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            if (row.get("bench") or "").strip() != "scheduler":
                continue
            mode = (row.get("mode") or "").strip()
            solver = parse_solver((row.get("notes") or "").strip())
            ticks = int((row.get("ticks_total") or "0").strip() or "0")
            exp = int((row.get("expected_bits_per_tick") or "0").strip() or "0")
            uniq = float((row.get("vmrep_avg_bits_uniq_dst_per_tick") or "0").strip() or "0")
            util = (uniq / exp) if exp > 0 else 0.0
            data[(mode, solver)] = (ticks, util)

    modes = sorted({m for (m, _s) in data.keys()})

    deltas_ticks: List[int] = []
    deltas_util: List[float] = []
    baseline_ticks: List[int] = []
    greedy_ticks: List[int] = []
    paired = 0

    for m in modes:
        if (m, "baseline") in data and (m, "greedy") in data:
            tb, ub = data[(m, "baseline")]
            tg, ug = data[(m, "greedy")]
            deltas_ticks.append(tb - tg)
            deltas_util.append(ug - ub)
            baseline_ticks.append(tb)
            greedy_ticks.append(tg)
            paired += 1

    if paired == 0:
        raise SystemExit("ERROR: no paired (baseline,greedy) rows found")

    better = sum(1 for d in deltas_ticks if d > 0)
    equal  = sum(1 for d in deltas_ticks if d == 0)
    worse  = sum(1 for d in deltas_ticks if d < 0)
    avg_dt = sum(deltas_ticks) / paired
    avg_du = sum(deltas_util) / paired

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Plot 1: histogram of delta ticks (baseline - greedy)
    plt.figure(figsize=(7.5,4.2))
    xmin = min(deltas_ticks)
    xmax = max(deltas_ticks)
    bins = list(range(xmin, xmax + 2))  # integer bins
    plt.hist(deltas_ticks, bins=bins, align="left", rwidth=0.9)
    plt.title("Scheduler ref_pack: Δticks (baseline - greedy)\\n"
              f"N={paired}  better={better}  equal={equal}  worse={worse}  avg={avg_dt:.2f}", fontsize=12)
    plt.xlabel("Δticks")
    plt.ylabel("instances")
    plt.xticks(list(range(xmin, xmax + 1)))
    plt.grid(True, axis="y", alpha=0.3)
    p1 = outdir / "delta_ticks_hist.png"
    plt.tight_layout()
    plt.savefig(p1, dpi=180, bbox_inches="tight")
    plt.close()

    # Plot 2: histogram of delta utilization, excluding zeros
    zeros = sum(1 for d in deltas_util if abs(d) < 1e-15)
    nz = [d for d in deltas_util if d > 1e-15]
    plt.figure(figsize=(7.5,4.2))
    if nz:
        plt.hist(nz, bins=30, rwidth=0.9)
    plt.title("Scheduler ref_pack: Δutilization (greedy - baseline), Δ>0 only\\n"
              f"N={paired}  zeros={zeros}  avg(all)={avg_du:.4f}", fontsize=12)
    plt.xlabel("Δutilization")
    plt.ylabel("instances")
    plt.grid(True, axis="y", alpha=0.3)
    p2 = outdir / "delta_util_pos_hist.png"
    plt.tight_layout()
    plt.savefig(p2, dpi=180, bbox_inches="tight")
    plt.close()

    # Plot 3: scatter baseline vs greedy ticks (points below diagonal are improvements)
    plt.figure(figsize=(5.4,5.4))

    eq_x, eq_y = [], []
    better_x, better_y = [], []
    worse_x, worse_y = [], []

    for x, y in zip(baseline_ticks, greedy_ticks):
        if y < x:
            better_x.append(x); better_y.append(y)
        elif y == x:
            eq_x.append(x); eq_y.append(y)
        else:
            worse_x.append(x); worse_y.append(y)

    plt.scatter(eq_x, eq_y, s=22, alpha=0.65, label="equal")
    plt.scatter(better_x, better_y, s=28, alpha=0.85, label="greedy better")
    if worse_x:
        plt.scatter(worse_x, worse_y, s=28, alpha=0.85, color="red", label="greedy worse")

    lo = min(min(baseline_ticks), min(greedy_ticks))
    hi = max(max(baseline_ticks), max(greedy_ticks))
    plt.plot([lo, hi], [lo, hi], linestyle='--', linewidth=1.0)

    plt.title("Scheduler ref_pack: ticks_total (baseline vs greedy)\\npoints below diagonal = improvement", fontsize=12)
    plt.xlabel("baseline ticks_total")
    plt.ylabel("greedy ticks_total")
    plt.grid(True, alpha=0.3)
    plt.legend(loc='best', frameon=True)

    p3 = outdir / "ticks_scatter.png"
    plt.tight_layout()
    plt.savefig(p3, dpi=180, bbox_inches="tight")
    plt.close()

    print("paired_instances:", paired)
    print("greedy_better (Δticks>0):", better)
    print("greedy_equal  (Δticks=0):", equal)
    print("greedy_worse  (Δticks<0):", worse)
    print("avg_delta_ticks:", avg_dt)
    print("avg_delta_util:", avg_du)
    print("wrote:", p1)
    print("wrote:", p2)
    print("wrote:", p3)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
