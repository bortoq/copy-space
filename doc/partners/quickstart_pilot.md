# Quickstart (pilot v0)

Goal: CSV demands -> validated schedule + metrics (STRICT1, volume-based).

Recommended: run the pilot in one command.
## Option A: one-command pilot

1) Prepare demands.csv with columns: src_slot,dst_slot,bits_total
Example:
src_slot,dst_slot,bits_total
0,1,4096
2,3,256

2) Run:
./scripts/scheduler/pilot_run.sh --csv demands.csv --bw 256 --outdir tmp/pilot
Outputs (tmp/pilot):
- instance.json
- schedule_baseline.json, schedule_greedy.json
- report_baseline.json, report_greedy.json

The script prints a short summary: ticks/utilization/delta.
## Validate-only (if you already have a schedule)

If you can export simple lines "tick src dst len_bits", convert to Schedule v0 JSON:
python3 scripts/scheduler/lines_to_schedule_v0.py schedule.txt --out schedule.json

Then validate + report:
python3 scripts/scheduler/validate_v0.py instance.json schedule.json --report report.json --quiet
