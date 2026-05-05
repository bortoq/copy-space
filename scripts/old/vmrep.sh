#!/bin/sh
set -eu

usage () {
  cat >&2 <<EOF
usage:
  scripts/vmrep.sh [all|fulladder|add8|eq24|eq24p|lt24|add24] [options]

options:
  --from N     start tick for throughput window (0-based)
  --len  L     length of throughput window in ticks (if omitted or 0 -> throughput report disabled)
  --hz   HZ    optional clock_hz for Gb/s print in vmrep (e.g. 1000000000)

examples:
  # latency only (still prints avg bits/tick)
  scripts/vmrep.sh eq24p

  # throughput window
  scripts/vmrep.sh eq24p --from 2000 --len 5000

  # run all tests with vmrep
  scripts/vmrep.sh all --from 0 --len 999999999
EOF
}

case "${1:-}" in
  ""|-h|--help) usage; exit 0 ;;
esac

TARGET="$1"
shift

FROM="${COPYSPACE_REPORT_FROM:-0}"
LEN="${COPYSPACE_REPORT_LEN:-0}"
HZ="${COPYSPACE_REPORT_HZ:-0}"

while [ $# -gt 0 ]; do
  case "$1" in
    --from) shift; FROM="${1:-}";;
    --len)  shift; LEN="${1:-}";;
    --hz)   shift; HZ="${1:-}";;
    *) echo "ERROR: unknown arg: $1" >&2; usage; exit 2 ;;
  esac
  shift
done

export COPYSPACE_REPORT=1
export COPYSPACE_REPORT_FROM="$FROM"
export COPYSPACE_REPORT_LEN="$LEN"
export COPYSPACE_REPORT_HZ="$HZ"

if [ "$TARGET" = "all" ]; then
  export ONLY=""
else
  export ONLY="$TARGET"
fi

exec scripts/test_all.sh