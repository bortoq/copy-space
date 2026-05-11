#!/bin/sh
set -eu

if [ "${1:-}" != "--row" ]; then
  echo "usage: $0 --row" >&2
  exit 2
fi

: "${INST_PATH:?need INST_PATH}"
: "${SOLVER:?need SOLVER (baseline|greedy|external)}"

python3 scripts/scheduler/sched_to_csv_row_v0.py --instance "$INST_PATH" --solver "$SOLVER"
