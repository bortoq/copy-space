#!/usr/bin/env python3
import argparse
import json
import math
import sys

MODEL = "STRICT1"

def eprint(*a):
    print(*a, file=sys.stderr)

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def fail_report(model, kind, msg, **ctx):
    err = {"kind": kind, "msg": msg}
    err.update(ctx)
    return {
        "status": "FAIL",
        "version": 0,
        "model": model,
        "errors": [err],
    }

def pass_report(model):
    return {
        "status": "PASS",
        "version": 0,
        "model": model,
        "errors": [],
    }

def inst_get_demands(inst):
    d = inst.get("demands", [])
    return d if isinstance(d, list) else []

def demand_map(inst, slots):
    dm = {}
    for i, d in enumerate(inst_get_demands(inst)):
        if not isinstance(d, dict):
            raise ValueError(f"demand[{i}] is not an object")
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
        dm[(s, t)] = dm.get((s, t), 0) + b
    return dm

def compute_max_degree_chunks(dm, bw, slots):
    if bw <= 0:
        return 0
    deg = [0] * slots
    for (s, t), bits in dm.items():
        ch = (bits + bw - 1) // bw
        deg[s] += ch
        deg[t] += ch
    return max(deg) if deg else 0
def validate_core_v0(inst, sched):
    # instance basic fields
    if inst.get("version") != 0:
        return fail_report(inst.get("model", "?"), "STRUCT", "instance.version must be 0")
    model = inst.get("model")
    if model != MODEL:
        return fail_report(str(model), "STRUCT", 'instance.model must be "STRICT1"')
    slots = inst.get("slots")
    bw = inst.get("copy_bw_bits_per_tick")
    if not isinstance(slots, int) or slots <= 0:
        return fail_report(model, "STRUCT", "instance.slots must be int > 0")
    if not isinstance(bw, int) or bw <= 0:
        return fail_report(model, "STRUCT", "instance.copy_bw_bits_per_tick must be int > 0")

    # schedule basic fields
    if not isinstance(sched, dict):
        return fail_report(model, "STRUCT", "schedule must be a JSON object")
    if sched.get("version") != 0:
        return fail_report(model, "STRUCT", "schedule.version must be 0")
    if sched.get("model") != model:
        return fail_report(model, "STRUCT", "schedule.model must match instance.model")
    ticks = sched.get("ticks")
    if not isinstance(ticks, list):
        return fail_report(model, "STRUCT", "schedule.ticks must be a list")

    # validate ticks + accumulate scheduled bits
    scheduled = {}
    bits_total = 0
    for ti, tick in enumerate(ticks):
        if not isinstance(tick, list):
            return fail_report(model, "STRUCT", "tick must be a list", tick=ti)
        used = set()
        for ci, ch in enumerate(tick):
            if not isinstance(ch, dict):
                return fail_report(model, "STRUCT", "chunk must be an object", tick=ti, chunk=ci)
            s = ch.get("src_slot")
            t = ch.get("dst_slot")
            l = ch.get("len_bits")
            if not isinstance(s, int) or not isinstance(t, int) or not isinstance(l, int):
                return fail_report(model, "STRUCT", "chunk fields must be integers", tick=ti, chunk=ci)
            if s < 0 or s >= slots or t < 0 or t >= slots:
                return fail_report(model, "STRUCT", "slot out of bounds", tick=ti, chunk=ci, src_slot=s, dst_slot=t)
            if s == t:
                return fail_report(model, "STRUCT", "src_slot == dst_slot", tick=ti, chunk=ci, slot=s)
            if l <= 0 or l > bw:
                return fail_report(model, "BW", "len_bits out of range", tick=ti, chunk=ci, len_bits=l, bw=bw)

            # STRICT1: participation at most once per tick
            if s in used or t in used:
                return fail_report(
                    model, "STRICT1", "slot participates more than once in a tick",
                    tick=ti, chunk=ci, src_slot=s, dst_slot=t
                )
            used.add(s); used.add(t)

            scheduled[(s, t)] = scheduled.get((s, t), 0) + l
            bits_total += l

    # coverage (required if demands non-empty)
    dm = demand_map(inst, slots)  # may be empty
    coverage_required = (len(dm) > 0)
    if coverage_required:
        # no extras
        for pair, sbits in scheduled.items():
            if pair not in dm:
                s, t = pair
                return fail_report(model, "EXTRAS", "scheduled pair not present in demands",
                                   src_slot=s, dst_slot=t, scheduled_bits=sbits)
        # exact coverage
        for pair, dbits in dm.items():
            sbits = scheduled.get(pair, 0)
            if sbits != dbits:
                s, t = pair
                kind = "COVERAGE_UNDER" if sbits < dbits else "COVERAGE_OVER"
                return fail_report(model, "COVERAGE", "demand coverage mismatch",
                                   subkind=kind, src_slot=s, dst_slot=t, demand_bits=dbits, scheduled_bits=sbits)

    # PASS + metrics
    rep = pass_report(model)
    ticks_total = len(ticks)
    rep["ticks_total"] = ticks_total
    rep["bits_total"] = bits_total
    rep["bits_per_tick"] = (bits_total / ticks_total) if ticks_total > 0 else 0.0
    rep["expected_bits_per_tick"] = (slots // 2) * bw
    rep["utilization"] = (rep["bits_per_tick"] / rep["expected_bits_per_tick"]) if rep["expected_bits_per_tick"] > 0 else 0.0
    rep["max_degree_chunks"] = compute_max_degree_chunks(dm, bw, slots) if coverage_required else 0
    return rep
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance_json")
    ap.add_argument("schedule_json")
    ap.add_argument("--report", default=None)
    ap.add_argument("--quiet", action="store_true", help="suppress PASS/FAIL prints")
    args = ap.parse_args()

    try:
        inst = load_json(args.instance_json)
        sched = load_json(args.schedule_json)
    except Exception as e:
        eprint("ERROR: failed to read/parse JSON:", e)
        return 1

    try:
        rep = validate_core_v0(inst, sched)
    except Exception as e:
        eprint("ERROR: invalid instance/schedule structure:", e)
        return 1

    ok = (rep.get("status") == "PASS")
    if ok:
        if not args.quiet: eprint("VALIDATION: PASS")
        rc = 0
    else:
        if not args.quiet: eprint("VALIDATION: FAIL")
        err = rep.get("errors", [{}])[0] if isinstance(rep.get("errors"), list) and rep.get("errors") else {}
        if err:
            eprint("reason:", err.get("kind", "?"), "-", err.get("msg", ""))
        rc = 2

    if args.report:
        try:
            with open(args.report, "w", encoding="utf-8") as f:
                json.dump(rep, f, indent=2, sort_keys=True)
                f.write("\n")
        except Exception as e:
            eprint("ERROR: failed to write report:", e)
            return 1

    return rc

if __name__ == "__main__":
    raise SystemExit(main())
