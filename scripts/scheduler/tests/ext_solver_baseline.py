#!/usr/bin/env python3
import json
import os
import sys

MODEL = "STRICT1"

def eprint(*a):
    print(*a, file=sys.stderr)

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def dump_json(path: str, obj: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")

def parse_instance(inst: dict) -> tuple[int, int, list[dict]]:
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
    demands = inst.get("demands", []) or []
    if not isinstance(demands, list):
        raise ValueError("instance.demands must be a list")
    return slots, bw, demands

def chunk_demands(demands: list[dict], bw: int) -> list[dict]:
    pending: list[dict] = []
    for d in demands:
        s = int(d["src_slot"])
        t = int(d["dst_slot"])
        bits = int(d["bits_total"])
        full = bits // bw
        rem = bits % bw
        for _ in range(full):
            pending.append({"src_slot": s, "dst_slot": t, "len_bits": bw})
        if rem:
            pending.append({"src_slot": s, "dst_slot": t, "len_bits": rem})
    return pending

def solve_baseline_strict1(pending: list[dict]) -> list[list[dict]]:
    ticks: list[list[dict]] = []
    while pending:
        used: set[int] = set()
        tick: list[dict] = []
        new_pending: list[dict] = []
        for ch in pending:
            s = int(ch["src_slot"])
            t = int(ch["dst_slot"])
            if s in used or t in used:
                new_pending.append(ch)
            else:
                tick.append(ch)
                used.add(s)
                used.add(t)
        if not tick:
            raise RuntimeError("solver made no progress (empty tick)")
        ticks.append(tick)
        pending = new_pending
    return ticks

def main() -> int:
    inst_path = os.environ.get("COPYSPACE_INSTANCE_JSON", "")
    out_path = os.environ.get("COPYSPACE_SCHEDULE_OUT", "")

    if not inst_path or not out_path:
        eprint("ERROR: missing env COPYSPACE_INSTANCE_JSON or COPYSPACE_SCHEDULE_OUT")
        return 2

    try:
        inst = load_json(inst_path)
        _slots, bw, demands = parse_instance(inst)
        pending = chunk_demands(demands, bw)
        ticks = solve_baseline_strict1(pending)
    except Exception as e:
        eprint("ERROR:", e)
        return 1

    sched = {"version": 0, "model": MODEL, "ticks": ticks}
    dump_json(out_path, sched)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
