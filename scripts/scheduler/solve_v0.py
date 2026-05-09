#!/usr/bin/env python3
import argparse
import json
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

def chunk_demands(demands, bw):
    pending = []
    for d in demands:
        s = d["src_slot"]; t = d["dst_slot"]; bits = d["bits_total"]
        full = bits // bw
        rem = bits % bw
        for _ in range(full):
            pending.append({"src_slot": s, "dst_slot": t, "len_bits": bw})
        if rem:
            pending.append({"src_slot": s, "dst_slot": t, "len_bits": rem})
    return pending

def solve_baseline_strict1(pending):
    ticks = []
    while pending:
        used = set()
        tick = []
        new_pending = []
        for ch in pending:
            s = ch["src_slot"]; t = ch["dst_slot"]
            if s in used or t in used:
                new_pending.append(ch)
            else:
                tick.append(ch)
                used.add(s); used.add(t)
        if not tick:
            raise RuntimeError("solver made no progress (empty tick)")
        ticks.append(tick)
        pending = new_pending
    return ticks

def _pending_degrees(pending):
    deg = {}
    for ch in pending:
        s = ch["src_slot"]; t = ch["dst_slot"]
        deg[s] = deg.get(s, 0) + 1
        deg[t] = deg.get(t, 0) + 1
    return deg

def solve_greedy_strict1(pending):
    """
    Deterministic greedy: each tick picks chunks incident to the most constrained slots first.
    Implementation:
      - compute current per-slot degrees from pending (incident chunk counts)
      - iterate pending indices sorted by score desc:
          score = deg[src] + deg[dst], tie-break by (src,dst,len_bits,original_index)
      - select chunk if both endpoints are unused in this tick
      - deferred chunks keep original order (important for determinism and fairness)
    """
    ticks = []
    while pending:
        deg = _pending_degrees(pending)
        order = list(range(len(pending)))

        def key(i):
            ch = pending[i]
            s = ch["src_slot"]; t = ch["dst_slot"]; l = ch["len_bits"]
            score = deg.get(s, 0) + deg.get(t, 0)
            return (-score, s, t, -l, i)

        order.sort(key=key)

        used = set()
        tick = []
        chosen = [False] * len(pending)

        for i in order:
            ch = pending[i]
            s = ch["src_slot"]; t = ch["dst_slot"]
            if s in used or t in used:
                continue
            tick.append(ch)
            chosen[i] = True
            used.add(s); used.add(t)

        if not tick:
            raise RuntimeError("greedy solver made no progress (empty tick)")

        new_pending = [pending[i] for i in range(len(pending)) if not chosen[i]]
        ticks.append(tick)
        pending = new_pending

    return ticks
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance_json")
    ap.add_argument("--out", required=True, help="output schedule JSON path")
    ap.add_argument("--solver", choices=["baseline", "greedy"], default="baseline")
    args = ap.parse_args()

    try:
        inst = load_json(args.instance_json)
        slots, bw, demands = parse_instance(inst)
    except Exception as e:
        eprint("ERROR:", e)
        return 1

    pending = chunk_demands(demands, bw)

    try:
        if args.solver == "baseline":
            ticks = solve_baseline_strict1(pending)
        else:
            ticks = solve_greedy_strict1(pending)
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
