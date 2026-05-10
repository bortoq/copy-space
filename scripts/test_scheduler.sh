#!/bin/sh
set -eu

PY=python3
V=./scripts/scheduler/validate_v0.py
S=./scripts/scheduler/solve_v0.py
T=scripts/scheduler/tests

run_expect() {
  inst="$1"
  sched="$2"
  exp="$3"

  set +e
  $PY "$V" "$inst" "$sched" >/dev/null 2>/dev/null
  rc=$?
  set -e

  if [ "$rc" -ne "$exp" ]; then
    echo "FAIL: expected rc=$exp got rc=$rc inst=$inst sched=$sched" >&2
    exit 1
  fi
}

run_validate_ok() {
  inst="$1"
  sched="$2"
  set +e
  $PY "$V" "$inst" "$sched" >/dev/null 2>/dev/null
  rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then
    echo "FAIL: expected PASS got rc=$rc inst=$inst sched=$sched" >&2
    exit 1
  fi
}

# PASS (no demands => no coverage check)
run_expect "$T/nodemands.instance.json" "$T/pass_minimal.schedule.json" 0

# PASS (demands => coverage required)
run_expect "$T/demands.instance.json" "$T/pass_coverage.schedule.json" 0

# FAIL: STRICT1 conflict
run_expect "$T/nodemands.instance.json" "$T/fail_strict1.schedule.json" 2

# FAIL: bandwidth
run_expect "$T/nodemands.instance.json" "$T/fail_bw.schedule.json" 2

# FAIL: coverage under
run_expect "$T/demands.instance.json" "$T/fail_coverage_under.schedule.json" 2

# FAIL: extras
run_expect "$T/demands.instance.json" "$T/fail_extras.schedule.json" 2

# FAIL: parse error (invalid JSON)
run_expect "$T/fail_parse.instance.json" "$T/pass_minimal.schedule.json" 1

# Solver smoke: baseline -> schedule must validate
tmp="$(mktemp)"
$PY "$S" "$T/demands.instance.json" --out "$tmp" --solver baseline >/dev/null 2>/dev/null
run_validate_ok "$T/demands.instance.json" "$tmp"
rm -f "$tmp"

# Solver smoke: greedy -> schedule must validate
tmp="$(mktemp)"
$PY "$S" "$T/demands.instance.json" --out "$tmp" --solver greedy >/dev/null 2>/dev/null
run_validate_ok "$T/demands.instance.json" "$tmp"
rm -f "$tmp"

# --- Adversarial / edge-case solver smokes ---
for inst in \
  "$T/edge_2slots.instance.json" \
  "$T/edge_2slots_dupdemands.instance.json" \
  "$T/adv_star_8.instance.json" \
  "$T/adv_cycle_8.instance.json"
do
  for solver in baseline greedy; do
    tmp="$(mktemp)"
    $PY "$S" "$inst" --out "$tmp" --solver "$solver" >/dev/null 2>/dev/null
    run_validate_ok "$inst" "$tmp"
    rm -f "$tmp"
  done
done

echo "OK: scheduler validator+solver tests passed"
