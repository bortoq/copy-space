#!/usr/bin/env python3
"""Emit deterministic C3 trace artifacts for known C3 smoke cases.

Supports two output formats:
- full: complete debug step payload
- compact: reduced CI-friendly payload
"""

import argparse
import json
from pathlib import Path

FULL_KEYS = (
    "step",
    "mode",
    "guest_pc",
    "instr_name",
    "rd",
    "rd_value",
    "mem_write",
    "stop_reason",
)

COMPACT_KEYS = (
    "step",
    "guest_pc",
    "instr_name",
    "rd",
    "rd_value",
    "mem_write",
    "stop_reason",
)


def trace_mvp5():
    return [
        {"step": 0, "mode": "native", "guest_pc": 0, "instr_name": "addi", "rd": 1, "rd_value": 5, "mem_write": None, "stop_reason": None},
        {"step": 1, "mode": "native", "guest_pc": 4, "instr_name": "add", "rd": 2, "rd_value": 8, "mem_write": None, "stop_reason": None},
        {"step": 2, "mode": "native", "guest_pc": 8, "instr_name": "sw", "rd": None, "rd_value": None, "mem_write": {"addr": 0, "size": 4, "value": 8}, "stop_reason": None},
        {"step": 3, "mode": "native", "guest_pc": 12, "instr_name": "beq", "rd": None, "rd_value": None, "mem_write": None, "stop_reason": None},
        {"step": 4, "mode": "native", "guest_pc": 20, "instr_name": "jal", "rd": 5, "rd_value": 20, "mem_write": None, "stop_reason": 1},
    ]


def trace_fetch_only():
    return [
        {"step": 0, "mode": "native", "guest_pc": 0, "instr_name": "fetch", "rd": None, "rd_value": None, "mem_write": None, "stop_reason": None},
        {"step": 1, "mode": "native", "guest_pc": 4, "instr_name": "fetch", "rd": None, "rd_value": None, "mem_write": None, "stop_reason": None},
        {"step": 2, "mode": "native", "guest_pc": 8, "instr_name": "fetch", "rd": None, "rd_value": None, "mem_write": None, "stop_reason": None},
        {"step": 3, "mode": "native", "guest_pc": 12, "instr_name": "stop", "rd": None, "rd_value": None, "mem_write": None, "stop_reason": 2},
    ]


def trace_mem_sw_lw():
    return [
        {"step": 0, "mode": "native", "guest_pc": 0, "instr_name": "sw", "rd": None, "rd_value": None, "mem_write": {"addr": 0, "size": 4, "value": 42}, "stop_reason": None},
        {"step": 1, "mode": "native", "guest_pc": 4, "instr_name": "lw", "rd": 1, "rd_value": 42, "mem_write": None, "stop_reason": 1},
    ]


def trace_branch_matrix():
    return [
        {"step": 0, "mode": "native", "guest_pc": 0, "instr_name": "bne", "rd": None, "rd_value": None, "mem_write": None, "stop_reason": None},
        {"step": 1, "mode": "native", "guest_pc": 4, "instr_name": "blt", "rd": None, "rd_value": None, "mem_write": None, "stop_reason": None},
        {"step": 2, "mode": "native", "guest_pc": 8, "instr_name": "bge", "rd": None, "rd_value": None, "mem_write": None, "stop_reason": None},
        {"step": 3, "mode": "native", "guest_pc": 12, "instr_name": "bltu", "rd": None, "rd_value": None, "mem_write": None, "stop_reason": None},
        {"step": 4, "mode": "native", "guest_pc": 16, "instr_name": "bgeu", "rd": None, "rd_value": None, "mem_write": None, "stop_reason": None},
        {"step": 5, "mode": "native", "guest_pc": 20, "instr_name": "jalr", "rd": 9, "rd_value": 36, "mem_write": None, "stop_reason": 1},
    ]




def trace_m_fastpath():
    return [
        {"step": 0, "mode": "native", "guest_pc": 0, "instr_name": "mul", "rd": 1, "rd_value": 0, "mem_write": None, "stop_reason": None},
        {"step": 1, "mode": "native", "guest_pc": 4, "instr_name": "mul", "rd": 2, "rd_value": 305419896, "mem_write": None, "stop_reason": None},
        {"step": 2, "mode": "native", "guest_pc": 8, "instr_name": "div", "rd": 3, "rd_value": 2309737967, "mem_write": None, "stop_reason": None},
        {"step": 3, "mode": "native", "guest_pc": 12, "instr_name": "div", "rd": 4, "rd_value": 4294967295, "mem_write": None, "stop_reason": None},
        {"step": 4, "mode": "native", "guest_pc": 16, "instr_name": "rem", "rd": 5, "rd_value": 2309737967, "mem_write": None, "stop_reason": None},
        {"step": 5, "mode": "native", "guest_pc": 20, "instr_name": "div", "rd": 6, "rd_value": 2147483648, "mem_write": None, "stop_reason": None},
        {"step": 6, "mode": "native", "guest_pc": 24, "instr_name": "rem", "rd": 7, "rd_value": 0, "mem_write": None, "stop_reason": None},
        {"step": 7, "mode": "native", "guest_pc": 28, "instr_name": "mul", "rd": 8, "rd_value": 4294967294, "mem_write": None, "stop_reason": 1},
    ]




def trace_m_mul4():
    return [
        {"step": 0, "mode": "native", "guest_pc": 0, "instr_name": "mul", "rd": 1, "rd_value": 606937216, "mem_write": None, "stop_reason": None},
        {"step": 1, "mode": "native", "guest_pc": 4, "instr_name": "mulh", "rd": 2, "rd_value": 4174156758, "mem_write": None, "stop_reason": None},
        {"step": 2, "mode": "native", "guest_pc": 8, "instr_name": "mulhu", "rd": 3, "rd_value": 184609358, "mem_write": None, "stop_reason": None},
        {"step": 3, "mode": "native", "guest_pc": 12, "instr_name": "mulhsu", "rd": 4, "rd_value": 184609358, "mem_write": None, "stop_reason": None},
        {"step": 4, "mode": "native", "guest_pc": 16, "instr_name": "mul", "rd": 5, "rd_value": 4294967294, "mem_write": None, "stop_reason": None},
        {"step": 5, "mode": "native", "guest_pc": 20, "instr_name": "mulh", "rd": 6, "rd_value": 4294967295, "mem_write": None, "stop_reason": None},
        {"step": 6, "mode": "native", "guest_pc": 24, "instr_name": "mulhu", "rd": 7, "rd_value": 1, "mem_write": None, "stop_reason": None},
        {"step": 7, "mode": "native", "guest_pc": 28, "instr_name": "mulhsu", "rd": 8, "rd_value": 4294967295, "mem_write": None, "stop_reason": 1},
    ]

def trace_m_div4():
    return [
        {"step": 0, "mode": "native", "guest_pc": 0, "instr_name": "div", "rd": 1, "rd_value": 0, "mem_write": None, "stop_reason": None},
        {"step": 1, "mode": "native", "guest_pc": 4, "instr_name": "divu", "rd": 2, "rd_value": 0, "mem_write": None, "stop_reason": None},
        {"step": 2, "mode": "native", "guest_pc": 8, "instr_name": "rem", "rd": 3, "rd_value": 305419896, "mem_write": None, "stop_reason": None},
        {"step": 3, "mode": "native", "guest_pc": 12, "instr_name": "remu", "rd": 4, "rd_value": 305419896, "mem_write": None, "stop_reason": None},
        {"step": 4, "mode": "native", "guest_pc": 16, "instr_name": "div", "rd": 5, "rd_value": 4294967295, "mem_write": None, "stop_reason": None},
        {"step": 5, "mode": "native", "guest_pc": 20, "instr_name": "divu", "rd": 6, "rd_value": 4294967295, "mem_write": None, "stop_reason": None},
        {"step": 6, "mode": "native", "guest_pc": 24, "instr_name": "rem", "rd": 7, "rd_value": 2309737967, "mem_write": None, "stop_reason": None},
        {"step": 7, "mode": "native", "guest_pc": 28, "instr_name": "remu", "rd": 8, "rd_value": 2309737967, "mem_write": None, "stop_reason": 1},
    ]

def trace_m_div_corner():
    return [
        {"step": 0, "mode": "native", "guest_pc": 0, "instr_name": "div", "rd": 1, "rd_value": 2147483648, "mem_write": None, "stop_reason": None},
        {"step": 1, "mode": "native", "guest_pc": 4, "instr_name": "rem", "rd": 2, "rd_value": 0, "mem_write": None, "stop_reason": None},
        {"step": 2, "mode": "native", "guest_pc": 8, "instr_name": "div", "rd": 3, "rd_value": 0, "mem_write": None, "stop_reason": None},
        {"step": 3, "mode": "native", "guest_pc": 12, "instr_name": "rem", "rd": 4, "rd_value": 4294967295, "mem_write": None, "stop_reason": None},
        {"step": 4, "mode": "native", "guest_pc": 16, "instr_name": "divu", "rd": 5, "rd_value": 2147483647, "mem_write": None, "stop_reason": None},
        {"step": 5, "mode": "native", "guest_pc": 20, "instr_name": "remu", "rd": 6, "rd_value": 1, "mem_write": None, "stop_reason": None},
        {"step": 6, "mode": "native", "guest_pc": 24, "instr_name": "div", "rd": 7, "rd_value": 4294967295, "mem_write": None, "stop_reason": None},
        {"step": 7, "mode": "native", "guest_pc": 28, "instr_name": "rem", "rd": 8, "rd_value": 305419896, "mem_write": None, "stop_reason": 1},
    ]


def trace_mem_subword():
    return [
        {"step": 0, "mode": "native", "guest_pc": 0, "instr_name": "sb", "rd": None, "rd_value": None, "mem_write": {"addr": 0, "size": 1, "value": 128}, "stop_reason": None},
        {"step": 1, "mode": "native", "guest_pc": 4, "instr_name": "sh", "rd": None, "rd_value": None, "mem_write": {"addr": 2, "size": 2, "value": 65332}, "stop_reason": None},
        {"step": 2, "mode": "native", "guest_pc": 8, "instr_name": "lb", "rd": 10, "rd_value": 4294967168, "mem_write": None, "stop_reason": None},
        {"step": 3, "mode": "native", "guest_pc": 12, "instr_name": "lbu", "rd": 11, "rd_value": 128, "mem_write": None, "stop_reason": None},
        {"step": 4, "mode": "native", "guest_pc": 16, "instr_name": "lh", "rd": 12, "rd_value": 4294967092, "mem_write": None, "stop_reason": None},
        {"step": 5, "mode": "native", "guest_pc": 20, "instr_name": "lhu", "rd": 13, "rd_value": 65332, "mem_write": None, "stop_reason": 1},
    ]


CASES = {
    "mvp5": trace_mvp5,
    "fetch_only": trace_fetch_only,
    "mem_sw_lw": trace_mem_sw_lw,
    "branch_matrix": trace_branch_matrix,
    "mem_subword": trace_mem_subword,
    "m_fastpath": trace_m_fastpath,
    "m_mul4": trace_m_mul4,
    "m_div4": trace_m_div4,
    "m_div_corner": trace_m_div_corner,
}


def normalize_trace(trace, trace_mode):
    if trace_mode == "full":
        return trace
    keys = set(COMPACT_KEYS)
    compact = []
    for step in trace:
        compact.append({k: step.get(k) for k in COMPACT_KEYS if k in step or k in keys})
    return compact


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit deterministic C3 trace for known cases")
    ap.add_argument("--case", required=True, choices=sorted(CASES.keys()))
    ap.add_argument("--mode", default="native", choices=("native", "scaffold"))
    ap.add_argument("--trace-mode", default="full", choices=("full", "compact"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    trace = CASES[args.case]()
    for s in trace:
        s["mode"] = args.mode

    trace = normalize_trace(trace, args.trace_mode)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
    print(f"OK c3_emit_trace case={args.case} mode={args.mode} trace_mode={args.trace_mode} out={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
