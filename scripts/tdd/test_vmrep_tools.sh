#!/bin/sh
set -eu

# file: scripts/tdd/test_vmrep_tools.sh
# purpose: verify vmrep parsing tool (vmrep_to_csv.py) on a synthetic vmrep log

[ -f scripts/vmrep_to_csv.py ] || { echo "FAIL: missing scripts/vmrep_to_csv.py" >&2; exit 1; }

mkdir -p tmp

LOG="tmp/tdd_vmrep_synth.log"
cat >"$LOG" <<'VMREP'
[vmrep] REPORT latency
[vmrep] ticks_total=2
[vmrep] bits_sum_total=16
[vmrep] bits_uniq_dst_total=12
[vmrep] avg_bits_sum_per_tick=8.000
[vmrep] avg_bits_uniq_dst_per_tick=6.000
[vmrep] REPORT throughput
[vmrep] thr_from=0 thr_len=2 thr_ticks=2
[vmrep] thr_avg_bits_sum_per_tick=8.000
[vmrep] thr_avg_bits_uniq_dst_per_tick=6.000
[vmrep] VMREP_END
VMREP

OUT="$(python3 scripts/vmrep_to_csv.py --bench tdd --log "$LOG" --row-only)"

python3 - "$OUT" <<'PY'
import sys

line = sys.argv[1].strip()
cols = line.split(",")

COLS = [
    "schema_version",
    "bench",
    "mode",
    "seed",
    "space_bytes",
    "slots",
    "addr_bits",
    "ticks_total",
    "moved_bits_total",
    "vmrep_bits_sum_total",
    "vmrep_bits_uniq_dst_total",
    "vmrep_avg_bits_sum_per_tick",
    "vmrep_avg_bits_uniq_dst_per_tick",
    "thr_from",
    "thr_len",
    "thr_avg_bits_sum_per_tick",
    "thr_avg_bits_uniq_dst_per_tick",
    "notes",
    "git_rev",
    "copies_total",
    "expected_bits_per_tick",
]

def need(cond, msg):
    if not cond:
        raise SystemExit("FAIL: " + msg + f"\nOUT={line}")

need(len(cols) == len(COLS), f"wrong column count: got={len(cols)} expected={len(COLS)}")

m = dict(zip(COLS, cols))

need(m["schema_version"] == "csv.v0", "schema_version != csv.v0")
need(m["bench"] == "tdd", "bench != tdd")

need(m["ticks_total"] == "2", "ticks_total != 2")
need(m["moved_bits_total"] == "16", "moved_bits_total != 16")
need(m["vmrep_bits_sum_total"] == "16", "vmrep_bits_sum_total != 16")
need(m["vmrep_bits_uniq_dst_total"] == "12", "vmrep_bits_uniq_dst_total != 12")

need(m["vmrep_avg_bits_sum_per_tick"] == "8.000", "avg_bits_sum_per_tick != 8.000")
need(m["vmrep_avg_bits_uniq_dst_per_tick"] == "6.000", "avg_bits_uniq_dst_per_tick != 6.000")

need(m["thr_from"] == "0", "thr_from != 0")
need(m["thr_len"] == "2", "thr_len != 2")
need(m["thr_avg_bits_sum_per_tick"] == "8.000", "thr_avg_bits_sum_per_tick != 8.000")
need(m["thr_avg_bits_uniq_dst_per_tick"] == "6.000", "thr_avg_bits_uniq_dst_per_tick != 6.000")

need(m["git_rev"] != "", "git_rev is empty (expected git rev or env override)")

# appended metrics: absent for this synthetic test => empty
need(m["copies_total"] == "", "copies_total expected empty in synthetic test")
need(m["expected_bits_per_tick"] == "", "expected_bits_per_tick expected empty in synthetic test")

print("OK vmrep_to_csv selftest")
PY
