# Examples

File: examples/README.md

These examples are intended to be runnable via python-first CLI entrypoints.

------------------------------------------------------------

## Shuffle-like workload (8 slots)

Demands:
- examples/shuffle8.csv

Interpretation:
- 4 source slots (0..3) send equal volumes to 4 destination slots (4..7)
- This resembles a shuffle/materialization phase (many-to-many transfers)

Run pilot (creates instance, schedules, validator reports, and optional HTML plots):

    python3 -m pip install -e .
    copyspace-pilot --csv examples/shuffle8.csv --bw 256 --outdir tmp/pilot_shuffle8 --plot

Inspect:
- tmp/pilot_shuffle8/report_baseline.json
- tmp/pilot_shuffle8/report_greedy.json
- tmp/pilot_shuffle8/plot_baseline.html
- tmp/pilot_shuffle8/plot_greedy.html
