#!/bin/sh
set -eu

# file: scripts/tdd/test_vmrep_tools.sh
# date: 2026-05-05
# purpose: verify vmrep parsing tool (vmrep_to_csv.py) on a synthetic vmrep log

[ -f scripts/vmrep_to_csv.py ] || { echo "FAIL: missing scripts/vmrep_to_csv.py" >&2; exit 1; }

mkdir -p tmp

LOG="tmp/tdd_vmrep_synth.log"
cat > "$LOG" <<'LOGEOF'
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
LOGEOF

OUT="$(python3 scripts/vmrep_to_csv.py --bench tdd --log "$LOG" --row-only)"

# Expect:
# schema_version=1, bench=tdd, ticks_total=2, bits_sum_total=16, bits_uniq_dst_total=12,
# avg uniq dst per tick = 6.000
echo "$OUT" | grep -q '^1,tdd,' || { echo "FAIL: bad CSV prefix: $OUT" >&2; exit 1; }
echo "$OUT" | grep -q ',2,,'  || { echo "FAIL: expected ticks_total=2 somewhere: $OUT" >&2; exit 1; }
echo "$OUT" | grep -q ',16,12,8.000,6.000,' || { echo "FAIL: expected vmrep numbers missing: $OUT" >&2; exit 1; }

echo "OK vmrep_to_csv selftest"
