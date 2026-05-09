#!/bin/sh
set -eu

die() { echo "ERROR: $*" >&2; exit 1; }

# go to repo root
REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not in a git repo"
cd "$REPO"

echo "[prepush] repo=$REPO"

ALLOW_DIRTY=0
FAST=0

while [ $# -gt 0 ]; do
  case "$1" in
    --allow-dirty) ALLOW_DIRTY=1; shift;;
    --fast) FAST=1; shift;;
    *) die "unknown arg: $1";;
  esac
done

echo
echo "[prepush] git status:"
git status --porcelain || true

if [ "$ALLOW_DIRTY" -eq 0 ]; then
  if [ -n "$(git status --porcelain)" ]; then
    die "working tree not clean (use --allow-dirty if intentional)"
  fi
fi

echo
echo "[prepush] reminder: ensure doc/status.md is up to date for this change set"

echo
echo "[prepush] check: CI-critical script modes in HEAD"
git ls-tree -r HEAD \
  scripts/test_all.sh \
  scripts/tdd/run_all.sh \
  scripts/tdd/mkbench_bad_bounds.py \
  >/dev/null 2>&1 || die "expected CI scripts not found in HEAD"
git ls-tree -r HEAD scripts/test_all.sh scripts/tdd/run_all.sh scripts/tdd/mkbench_bad_bounds.py | cat

echo
echo "[prepush] build+tests (clean -> bins -> test -> tdd)"
make clean
make bins
make test
make tdd
./scripts/test_scheduler.sh

if [ "$FAST" -eq 1 ]; then
  echo
  echo "[prepush] --fast: skipping bench smokes"
  echo "[prepush] OK"
  exit 0
fi

echo
echo "[prepush] bench smoke: core benches"
mkdir -p tmp
scripts/bench/run.sh --bench all --out tmp/bench_smoke.csv \
  --repeat 1 \
  --copies-list 16 \
  --chunk-bytes-list 16 \
  --src-stride-bytes-list 4096 \
  --mode-list random \
  --seed-list 1 \
  --len-bytes-list 1024 \
  --life-list 100

python3 scripts/bench/summarize.py --in tmp/bench_smoke.csv --top 2 >/dev/null

echo
echo "[prepush] bench smoke: scheduler (unified CSV)"
scripts/bench/run.sh --bench scheduler --out tmp/sched_smoke.csv --repeat 1
python3 scripts/bench/summarize.py --in tmp/sched_smoke.csv --top 5 >/dev/null

echo
echo "[prepush] OK"
