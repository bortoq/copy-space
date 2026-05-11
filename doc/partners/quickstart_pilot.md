# Quickstart (pilot v0)

Goal: CSV demands -> validated schedule + metrics (STRICT1, volume-based).

This quickstart uses the Copy-Space CLI entrypoints (copyspace-*).

## Install

    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install -e .

## Option A: one-command pilot

1) Prepare demands.csv with columns:
   src_slot,dst_slot,bits_total

Example:
src_slot,dst_slot,bits_total
0,1,4096
2,3,256

2) Run:

    copyspace-pilot --csv demands.csv --bw 256 --outdir tmp/pilot

Outputs (tmp/pilot):
- instance.json
- schedule_baseline.json, schedule_greedy.json
- report_baseline.json, report_greedy.json

The command prints a short summary (ticks, utilization, deltas).

## Optional: write HTML plots (no extra dependencies)

This generates two simple HTML files to help onboarding:
- plot_baseline.html
- plot_greedy.html

Example:

    copyspace-pilot --csv demands.csv --bw 256 --outdir tmp/pilot --plot --plot-max-ticks 256

## Validate-only (if you already have a schedule)

If you can export simple lines:
tick src dst len_bits

Convert to Schedule v0 JSON:

    copyspace-lines-to-schedule schedule.txt --out schedule.json

Then validate and write a report:

    copyspace-validate instance.json schedule.json --report report.json --quiet
