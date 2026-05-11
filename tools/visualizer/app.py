#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import streamlit as st
import matplotlib.pyplot as plt

# Use in-repo package (works with `pip install -e .`).
from copyspace.v0.solve import (
    solve_baseline_strict1_demands,
    solve_greedy_strict1_demands,
)
from copyspace.v0.validate import validate_core_v0

st.set_page_config(page_title="Copy-Space Visualizer (v0)", layout="wide")

def load_json_bytes(b: bytes) -> Any:
    return json.loads(b.decode("utf-8"))

def load_json_path(p: str) -> Any:
    return json.loads(Path(p).read_text(encoding="utf-8"))

def build_schedule(inst: dict, solver: str) -> dict:
    bw = int(inst["copy_bw_bits_per_tick"])
    demands = inst.get("demands", []) or []
    if solver == "baseline":
        ticks = solve_baseline_strict1_demands(demands, bw)
    else:
        ticks = solve_greedy_strict1_demands(demands, bw)
    return {"version": 0, "model": inst["model"], "ticks": ticks}

def tick_slot_heatmap(inst: dict, sched: dict) -> plt.Figure:
    slots = int(inst["slots"])
    ticks = sched.get("ticks", []) or []
    T = len(ticks)
    # 0=unused, 1=src, 2=dst (dst overrides src if both would happen; STRICT1 prevents both)
    grid = [[0 for _ in range(T)] for _ in range(slots)]
    for ti, tick in enumerate(ticks):
        for ch in tick:
            s = int(ch["src_slot"]); d = int(ch["dst_slot"])
            if 0 <= s < slots: grid[s][ti] = 1
            if 0 <= d < slots: grid[d][ti] = 2

    fig, ax = plt.subplots(figsize=(min(12, max(6, T * 0.25)), min(10, max(4, slots * 0.22))))
    ax.imshow(grid, aspect="auto", interpolation="nearest")
    ax.set_title("Slot participation heatmap (0=unused, 1=src, 2=dst)")
    ax.set_xlabel("tick")
    ax.set_ylabel("slot")
    return fig

def tick_load_plot(sched: dict) -> plt.Figure:
    ticks = sched.get("ticks", []) or []
    loads = [len(t) for t in ticks]
    fig, ax = plt.subplots(figsize=(10, 2.8))
    ax.plot(loads, marker="o", linewidth=1.2)
    ax.set_title("Tick load (#chunks per tick)")
    ax.set_xlabel("tick")
    ax.set_ylabel("chunks")
    ax.grid(True, alpha=0.3)
    return fig

st.title("Copy-Space — Scheduler Visualizer (v0)")

left, right = st.columns([1, 1], gap="large")

with left:
    st.header("Inputs")

    default_inst = "scripts/scheduler/tests/demo_instance.json"
    default_sched = ""

    inst_mode = st.radio("Instance source", ["Use demo_instance.json", "Upload instance JSON"], index=0)
    if inst_mode == "Use demo_instance.json":
        inst = load_json_path(default_inst)
        st.caption(f"Using {default_inst}")
    else:
        up = st.file_uploader("Upload instance.json", type=["json"])
        inst = load_json_bytes(up.getvalue()) if up else None

    sched_mode = st.radio("Schedule source", ["Generate (choose solver)", "Upload schedule JSON"], index=0)

    solver = "baseline"
    sched = None

    if inst is not None and sched_mode == "Generate (choose solver)":
        solver = st.selectbox("Solver", ["baseline", "greedy"], index=1)
        if st.button("Generate schedule"):
            sched = build_schedule(inst, solver)
    elif inst is not None:
        up2 = st.file_uploader("Upload schedule.json", type=["json"])
        sched = load_json_bytes(up2.getvalue()) if up2 else None

with right:
    st.header("Validation + metrics")

    if inst is None:
        st.warning("Provide an instance first.")
    elif sched is None:
        st.info("Provide or generate a schedule.")
    else:
        rep = validate_core_v0(inst, sched)
        status = rep.get("status", "?")
        if status == "PASS":
            st.success("VALIDATION: PASS")
        else:
            st.error("VALIDATION: FAIL")
            st.json(rep.get("errors", []))

        # Metrics
        cols = st.columns(5)
        cols[0].metric("ticks_total", rep.get("ticks_total", "-"))
        cols[1].metric("bits_total", rep.get("bits_total", "-"))
        cols[2].metric("bits_per_tick", f"{rep.get('bits_per_tick', 0.0):.2f}" if "bits_per_tick" in rep else "-")
        cols[3].metric("expected_bits_per_tick", rep.get("expected_bits_per_tick", "-"))
        cols[4].metric("utilization", f"{rep.get('utilization', 0.0)*100.0:.1f}%" if "utilization" in rep else "-")

        st.caption(f"model={inst.get('model')} solver={solver if sched_mode.startswith('Generate') else 'external'}")

st.divider()
st.header("Visualization")

if inst is not None and sched is not None:
    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        st.pyplot(tick_slot_heatmap(inst, sched), clear_figure=True)
    with c2:
        st.pyplot(tick_load_plot(sched), clear_figure=True)

    with st.expander("Schedule (ticks)"):
        st.json(sched)
else:
    st.info("Generate/upload a schedule to see plots.")
