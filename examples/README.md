# Examples

## demands.csv
A tiny example demand list for a first run.

Recommended: install Copy-Space (enables copyspace-* commands):

    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install -e .

Run a pilot in one command:

    copyspace-pilot --csv examples/demands.csv --bw 256 --outdir tmp/pilot_example

Outputs (tmp/pilot_example):
- instance.json
- schedule_baseline.json, schedule_greedy.json
- report_baseline.json, report_greedy.json

See also: doc/partners/quickstart_pilot.md
