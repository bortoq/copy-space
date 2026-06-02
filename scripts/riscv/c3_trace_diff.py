#!/usr/bin/env python3
"""Compare C3 guest-step trace against Python RV32I reference trace.

Expected trace schema (JSON array of steps):
  {
    "guest_pc": int,
    "instr_name": str,
    "rd": int|null,
    "rd_value": int|null,
    "mem_write": {"addr":int,"size":int,"value":int}|null,
    "stop_reason": int|null
  }
"""

import argparse
import json
import sys
from pathlib import Path


REQUIRED_KEYS = ("guest_pc", "instr_name", "rd", "rd_value", "mem_write", "stop_reason")


def fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def load_trace(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"trace is not list: {path}")
    for i, step in enumerate(data):
        if not isinstance(step, dict):
            raise ValueError(f"trace[{i}] not object")
        for k in REQUIRED_KEYS:
            if k not in step:
                raise ValueError(f"trace[{i}] missing key '{k}'")
    return data


def same_mem(a, b):
    if a is None and b is None:
        return True
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    return (a.get("addr") == b.get("addr") and
            a.get("size") == b.get("size") and
            a.get("value") == b.get("value"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Diff C3 trace vs reference trace")
    ap.add_argument("--c3-trace", required=True)
    ap.add_argument("--ref-trace", required=True)
    args = ap.parse_args()

    c3 = load_trace(Path(args.c3_trace))
    ref = load_trace(Path(args.ref_trace))

    if len(c3) != len(ref):
        return fail(f"step length mismatch c3={len(c3)} ref={len(ref)}")

    for i, (a, b) in enumerate(zip(c3, ref)):
        for k in ("guest_pc", "instr_name", "rd", "rd_value", "stop_reason"):
            if a.get(k) != b.get(k):
                return fail(f"step {i} key '{k}' mismatch c3={a.get(k)} ref={b.get(k)}")
        if not same_mem(a.get("mem_write"), b.get("mem_write")):
            return fail(f"step {i} key 'mem_write' mismatch c3={a.get('mem_write')} ref={b.get('mem_write')}")

    print(f"OK c3_trace_diff steps={len(c3)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
