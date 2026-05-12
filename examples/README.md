# Examples

File: examples/README.md

These examples are intended to be runnable via python-first CLI entrypoints.

------------------------------------------------------------

## Hero: odd ring (non-trivial gap to lower bound)

Demands:
- examples/ring15.csv

Interpretation:
- 15 slots (0..14)
- each slot sends to the next one (i -> i+1, and 14 -> 0)
- this is an odd cycle workload, which tends to be non-trivial under STRICT1
- baseline vs greedy usually shows a clear gap-to-lower-bound difference

Run pilot (creates instance, schedules, validator reports, and optional HTML plots):

    python3 -m pip install -e .
    copyspace-pilot --csv examples/ring15.csv --bw 256 --outdir tmp/pilot_ring15 --plot

Inspect:
- tmp/pilot_ring15/report_baseline.json
- tmp/pilot_ring15/report_greedy.json
- tmp/pilot_ring15/plot_baseline.html
- tmp/pilot_ring15/plot_greedy.html

------------------------------------------------------------

## Secondary example: shuffle-like workload (16 slots)

Demands:
- examples/shuffle16.csv

Run:

    copyspace-pilot --csv examples/shuffle16.csv --bw 256 --outdir tmp/pilot_shuffle16 --plot
