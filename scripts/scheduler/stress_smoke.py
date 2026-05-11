#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def gen_demands(slots: int, bits_per_pair: int, pattern: str) -> list[dict]:
    if slots < 2:
        raise ValueError("slots must be >= 2")
    if bits_per_pair <= 0:
        raise ValueError("bits_per_pair must be > 0")

    demands: list[dict] = []

    if pattern == "full-mesh":
        for src in range(slots):
            for dst in range(slots):
                if dst == src:
                    continue
                demands.append({"src_slot": src, "dst_slot": dst, "bits_total": bits_per_pair})
        return demands

    if pattern == "star":
        src = 0
        for dst in range(slots):
            if dst == src:
                continue
            demands.append({"src_slot": src, "dst_slot": dst, "bits_total": bits_per_pair})
        return demands

    if pattern == "cycle":
        for src in range(slots):
            dst = (src + 1) % slots
            demands.append({"src_slot": src, "dst_slot": dst, "bits_total": bits_per_pair})
        return demands

    raise ValueError(f"unknown pattern: {pattern}")


def write_instance(path: Path, slots: int, bw: int, bits_per_pair: int, pattern: str, seed: int) -> dict:
    demands = gen_demands(slots=slots, bits_per_pair=bits_per_pair, pattern=pattern)

    inst = {
        "version": 0,
        "model": "STRICT1",
        "slots": slots,
        "copy_bw_bits_per_tick": bw,
        "demands": demands,
        "notes": (
            "stress_smoke v0; "
            f"pattern={pattern}; slots={slots}; bw={bw}; bits_per_pair={bits_per_pair}; seed={seed}"
        ),
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(inst, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return inst


def run_cmd(argv: list[str]) -> tuple[int, float, str, str]:
    t0 = time.time()
    p = subprocess.run(argv, capture_output=True, text=True)
    t1 = time.time()
    return p.returncode, (t1 - t0), (p.stdout or ""), (p.stderr or "")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Scheduler v0 stress smoke: generate instance, solve, validate.")
    ap.add_argument("--outdir", default="tmp/stress_smoke", help="output directory (instance + reports)")
    ap.add_argument("--slots", type=int, default=16)
    ap.add_argument("--bw", type=int, default=256, help="copy_bw_bits_per_tick")
    ap.add_argument("--bits-per-pair", type=int, default=65536)
    ap.add_argument("--pattern", choices=["full-mesh", "star", "cycle"], default="full-mesh")
    ap.add_argument("--seed", type=int, default=1, help="reserved for future random patterns; kept for determinism")
    ap.add_argument(
        "--solver-list",
        nargs="+",
        default=["baseline", "greedy"],
        choices=["baseline", "greedy", "external"],
        help="solvers to run",
    )
    ap.add_argument("--keep-schedule", action="store_true", help="keep schedule JSON files (default: delete)")
    args = ap.parse_args()

    if args.bw <= 0:
        raise SystemExit("bw must be > 0")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    inst_path = outdir / "instance.json"
    inst = write_instance(
        path=inst_path,
        slots=args.slots,
        bw=args.bw,
        bits_per_pair=args.bits_per_pair,
        pattern=args.pattern,
        seed=args.seed,
    )

    demands_n = len(inst["demands"])
    chunks_per_demand = (args.bits_per_pair + args.bw - 1) // args.bw
    chunks_total = demands_n * chunks_per_demand

    print("stress_smoke v0")
    print(f"outdir: {outdir}")
    print(f"instance: {inst_path}")
    print(f"pattern={args.pattern} slots={args.slots} bw={args.bw} bits_per_pair={args.bits_per_pair}")
    print(f"demands={demands_n} chunks_per_demand={chunks_per_demand} chunks_total={chunks_total}")
    print(f"solvers: {' '.join(args.solver_list)}")
    print()

    py = sys.executable
    solve = [py, "scripts/scheduler/solve_v0.py"]
    validate = [py, "scripts/scheduler/validate_v0.py"]

    summary: dict = {
        "pattern": args.pattern,
        "slots": args.slots,
        "bw": args.bw,
        "bits_per_pair": args.bits_per_pair,
        "demands": demands_n,
        "chunks_per_demand": chunks_per_demand,
        "chunks_total": chunks_total,
        "solver_results": {},
    }

    for solver in args.solver_list:
        sched_path = outdir / f"schedule_{solver}.json"
        rep_path = outdir / f"report_{solver}.json"

        solve_argv = solve + [str(inst_path), "--out", str(sched_path), "--solver", solver]
        rc_solve, solve_s, so, se = run_cmd(solve_argv)
        if rc_solve != 0:
            sys.stderr.write(f"FAIL: solve rc={rc_solve} solver={solver}\n")
            sys.stderr.write(f"cmd: {' '.join(solve_argv)}\n")
            if so.strip():
                sys.stderr.write("stdout:\n" + so[-4000:] + "\n")
            if se.strip():
                sys.stderr.write("stderr:\n" + se[-4000:] + "\n")
            return 2

        val_argv = validate + [str(inst_path), str(sched_path), "--report", str(rep_path), "--quiet"]
        rc_val, val_s, vo, ve = run_cmd(val_argv)
        if rc_val != 0:
            sys.stderr.write(f"FAIL: validate rc={rc_val} solver={solver}\n")
            sys.stderr.write(f"cmd: {' '.join(val_argv)}\n")
            if vo.strip():
                sys.stderr.write("stdout:\n" + vo[-4000:] + "\n")
            if ve.strip():
                sys.stderr.write("stderr:\n" + ve[-4000:] + "\n")
            return 2

        rep = load_json(rep_path)
        ticks_total = rep.get("ticks_total")
        lb = rep.get("lower_bound_ticks")
        gap = rep.get("gap_ticks")
        util = rep.get("utilization")
        bpt = rep.get("bits_per_tick")
        bits_total = rep.get("bits_total")

        print(
            "PASS: "
            f"solver={solver} "
            f"ticks_total={ticks_total} "
            f"lower_bound_ticks={lb} "
            f"gap_ticks={gap} "
            f"utilization={util} "
            f"bits_per_tick={bpt} "
            f"bits_total={bits_total} "
            f"solve_s={solve_s:.3f} "
            f"validate_s={val_s:.3f}"
        )

        summary["solver_results"][solver] = {
            "solve_s": solve_s,
            "validate_s": val_s,
            "report_path": str(rep_path),
            "schedule_path": str(sched_path) if args.keep_schedule else None,
            "ticks_total": ticks_total,
            "lower_bound_ticks": lb,
            "gap_ticks": gap,
            "gap_to_lower_bound": rep.get("gap_to_lower_bound"),
            "utilization": util,
            "bits_per_tick": bpt,
            "bits_total": bits_total,
        }

        if not args.keep_schedule:
            try:
                os.unlink(sched_path)
            except FileNotFoundError:
                pass

    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print()
    print(f"Wrote: {outdir / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
