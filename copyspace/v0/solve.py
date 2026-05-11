#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys

MODEL = "STRICT1"

def eprint(*a):
    print(*a, file=sys.stderr)

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def dump_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")

def parse_instance(inst):
    if not isinstance(inst, dict):
        raise ValueError("instance must be a JSON object")
    if inst.get("version") != 0:
        raise ValueError("instance.version must be 0")
    if inst.get("model") != MODEL:
        raise ValueError('instance.model must be "STRICT1"')
    slots = inst.get("slots")
    bw = inst.get("copy_bw_bits_per_tick")
    if not isinstance(slots, int) or slots <= 0:
        raise ValueError("instance.slots must be int > 0")
    if not isinstance(bw, int) or bw <= 0:
        raise ValueError("instance.copy_bw_bits_per_tick must be int > 0")
    demands = inst.get("demands", [])
    if demands is None:
        demands = []
    if not isinstance(demands, list):
        raise ValueError("instance.demands must be a list")
    for i, d in enumerate(demands):
        if not isinstance(d, dict):
            raise ValueError(f"demand[{i}] must be an object")
        s = d.get("src_slot")
        t = d.get("dst_slot")
        b = d.get("bits_total")
        if not isinstance(s, int) or not isinstance(t, int) or not isinstance(b, int):
            raise ValueError(f"demand[{i}] fields must be integers")
        if s < 0 or s >= slots or t < 0 or t >= slots:
            raise ValueError(f"demand[{i}] slot out of bounds")
        if s == t:
            raise ValueError(f"demand[{i}] src_slot == dst_slot")
        if b <= 0:
            raise ValueError(f"demand[{i}] bits_total must be > 0")
    return slots, bw, demands

def aggregate_demands(demands):
    dm = {}
    for d in demands:
        s = int(d["src_slot"])
        t = int(d["dst_slot"])
        b = int(d["bits_total"])
        dm[(s, t)] = dm.get((s, t), 0) + b
    out = []
    for (s, t), b in sorted(dm.items()):
        out.append({"src_slot": s, "dst_slot": t, "bits_total": b})
    return out

def demands_to_pending_volume(demands):
    pending = []
    for d in demands:
        pending.append(
            {
                "src_slot": int(d["src_slot"]),
                "dst_slot": int(d["dst_slot"]),
                "rem_bits": int(d["bits_total"]),
            }
        )
    return pending

def solve_baseline_strict1_volume(pending, bw):
    ticks = []
    while pending:
        used = set()
        tick = []
        new_pending = []
        for item in pending:
            s = item["src_slot"]
            t = item["dst_slot"]
            rem = item["rem_bits"]
            if s in used or t in used:
                new_pending.append(item)
                continue

            l = bw if rem > bw else rem
            tick.append({"src_slot": s, "dst_slot": t, "len_bits": l})
            used.add(s)
            used.add(t)

            rem2 = rem - l
            if rem2 > 0:
                new_pending.append({"src_slot": s, "dst_slot": t, "rem_bits": rem2})

        if not tick:
            raise RuntimeError("solver made no progress (empty tick)")
        ticks.append(tick)
        pending = new_pending

    return ticks

def _pending_degrees_volume(pending, bw):
    deg = {}
    for item in pending:
        s = item["src_slot"]
        t = item["dst_slot"]
        rem = item["rem_bits"]
        ch = (rem + bw - 1) // bw
        deg[s] = deg.get(s, 0) + ch
        deg[t] = deg.get(t, 0) + ch
    return deg

def solve_greedy_strict1_volume(pending, bw):
    """
    Deterministic greedy on the volume-based pending set.

    Each tick:
    - compute per-slot degrees from pending (in chunks, i.e. ceil(rem/bw))
    - sort pending indices by score desc:
        score = deg[src] + deg[dst]
      with deterministic tie-breakers
    - select an item if both endpoints are unused in this tick
    - emit one chunk (len_bits = min(bw, rem_bits))
    - keep remainder in pending, preserving original item order
    """
    ticks = []
    while pending:
        deg = _pending_degrees_volume(pending, bw)
        order = list(range(len(pending)))

        def key(i):
            it = pending[i]
            s = it["src_slot"]
            t = it["dst_slot"]
            rem = it["rem_bits"]
            l = bw if rem > bw else rem
            score = deg.get(s, 0) + deg.get(t, 0)
            return (-score, s, t, -l, i)

        order.sort(key=key)

        used = set()
        tick = []
        chosen = [False] * len(pending)
        chosen_len = [0] * len(pending)

        for i in order:
            it = pending[i]
            s = it["src_slot"]
            t = it["dst_slot"]
            if s in used or t in used:
                continue
            rem = it["rem_bits"]
            l = bw if rem > bw else rem
            tick.append({"src_slot": s, "dst_slot": t, "len_bits": l})
            chosen[i] = True
            chosen_len[i] = l
            used.add(s)
            used.add(t)

        if not tick:
            raise RuntimeError("greedy solver made no progress (empty tick)")

        new_pending = []
        for i in range(len(pending)):
            it = pending[i]
            if chosen[i]:
                rem2 = it["rem_bits"] - chosen_len[i]
                if rem2 > 0:
                    new_pending.append({"src_slot": it["src_slot"], "dst_slot": it["dst_slot"], "rem_bits": rem2})
            else:
                new_pending.append(it)

        ticks.append(tick)
        pending = new_pending

    return ticks

def solve_baseline_strict1_demands(demands, bw):
    demands2 = aggregate_demands(demands)
    pending = demands_to_pending_volume(demands2)
    return solve_baseline_strict1_volume(pending, bw)

def solve_greedy_strict1_demands(demands, bw):
    demands2 = aggregate_demands(demands)
    pending = demands_to_pending_volume(demands2)
    return solve_greedy_strict1_volume(pending, bw)


# Backwards compatibility helpers (legacy chunk-based API)
# Note: these may expand demands into per-bw chunks and can be memory-heavy.

def chunk_demands(demands, bw):
    pending = []
    for d in aggregate_demands(demands):
        s = int(d['src_slot'])
        t = int(d['dst_slot'])
        bits = int(d['bits_total'])
        full = bits // bw
        rem = bits % bw
        for _ in range(full):
            pending.append({'src_slot': s, 'dst_slot': t, 'len_bits': bw})
        if rem:
            pending.append({'src_slot': s, 'dst_slot': t, 'len_bits': rem})
    return pending

def solve_baseline_strict1(pending):
    ticks = []
    while pending:
        used = set()
        tick = []
        new_pending = []
        for ch in pending:
            s = ch['src_slot']
            t = ch['dst_slot']
            if s in used or t in used:
                new_pending.append(ch)
            else:
                tick.append(ch)
                used.add(s)
                used.add(t)
        if not tick:
            raise RuntimeError('solver made no progress (empty tick)')
        ticks.append(tick)
        pending = new_pending
    return ticks

def _pending_degrees(pending):
    deg = {}
    for ch in pending:
        s = ch['src_slot']
        t = ch['dst_slot']
        deg[s] = deg.get(s, 0) + 1
        deg[t] = deg.get(t, 0) + 1
    return deg

def solve_greedy_strict1(pending):
    ticks = []
    while pending:
        deg = _pending_degrees(pending)
        order = list(range(len(pending)))
        def key(i):
            ch = pending[i]
            s = ch['src_slot']
            t = ch['dst_slot']
            l = ch['len_bits']
            score = deg.get(s, 0) + deg.get(t, 0)
            return (-score, s, t, -l, i)
        order.sort(key=key)
        used = set()
        tick = []
        chosen = [False] * len(pending)
        for i in order:
            ch = pending[i]
            s = ch['src_slot']
            t = ch['dst_slot']
            if s in used or t in used:
                continue
            tick.append(ch)
            chosen[i] = True
            used.add(s)
            used.add(t)
        if not tick:
            raise RuntimeError('greedy solver made no progress (empty tick)')
        new_pending = [pending[i] for i in range(len(pending)) if not chosen[i]]
        ticks.append(tick)
        pending = new_pending
    return ticks

def run_external_solver(instance_json: str, out_json: str, argv: list[str]) -> int:
    inst_abs = os.path.abspath(instance_json)
    out_abs = os.path.abspath(out_json)

    env = dict(os.environ)
    env["COPYSPACE_INSTANCE_JSON"] = inst_abs
    env["COPYSPACE_SCHEDULE_OUT"] = out_abs
    env["COPYSPACE_MODEL"] = MODEL

    try:
        p = subprocess.run(argv, env=env)
    except FileNotFoundError as e:
        eprint("ERROR: external solver not found:", e)
        return 1
    except Exception as e:
        eprint("ERROR: failed to run external solver:", e)
        return 1

    if p.returncode != 0:
        eprint("ERROR: external solver returned non-zero exit:", p.returncode)
        return 1

    if not os.path.isfile(out_abs):
        eprint("ERROR: external solver did not produce schedule:", out_abs)
        return 1

    # sanity check: output must be JSON
    try:
        _ = load_json(out_abs)
    except Exception as e:
        eprint("ERROR: external solver output is not valid JSON:", e)
        return 1

    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance_json")
    ap.add_argument("--out", required=True, help="output schedule JSON path")
    ap.add_argument("--solver", choices=["baseline", "greedy", "external"], default="baseline")
    ap.add_argument(
        "--external-argv",
        nargs=argparse.REMAINDER,
        help="external solver command (use after --external-argv). "
             "The command receives env vars COPYSPACE_INSTANCE_JSON and COPYSPACE_SCHEDULE_OUT.",
    )
    args = ap.parse_args()

    if args.solver == "external":
        argv = args.external_argv or []
        if argv and argv[0] == "--":
            argv = argv[1:]
        if not argv:
            eprint("ERROR: --solver external requires --external-argv CMD [ARGS...]")
            return 1
        return run_external_solver(args.instance_json, args.out, argv)

    try:
        inst = load_json(args.instance_json)
        _slots, bw, demands = parse_instance(inst)
    except Exception as e:
        eprint("ERROR:", e)
        return 1

    try:
        if args.solver == "baseline":
            ticks = solve_baseline_strict1_demands(demands, bw)
        else:
            ticks = solve_greedy_strict1_demands(demands, bw)
    except Exception as e:
        eprint("ERROR:", e)
        return 1

    sched = {"version": 0, "model": MODEL, "ticks": ticks}
    try:
        dump_json(args.out, sched)
    except Exception as e:
        eprint("ERROR: failed to write schedule:", e)
        return 1

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
