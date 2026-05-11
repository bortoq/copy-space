---
name: Bug report
about: Report a bug / unexpected behavior (Scheduler v0, STRICT1)
title: "[bug] <short title>"
labels: ["bug"]
assignees: []
---

## What happened?
Describe the observed behavior (error, wrong metric, unexpected PASS/FAIL).

## What did you expect?
Describe expected behavior.

## How to reproduce
Please include exact commands you ran (copy/paste), preferably using the public CLI:
- copyspace-validate ...
- copyspace-solve ...
- copyspace-pilot ...

If you used internal scripts, include them too:
- python3 scripts/scheduler/validate_v0.py ...
- python3 scripts/scheduler/solve_v0.py ...

## Inputs (please attach)
- instance.json (Scheduler v0)
- schedule.json (Scheduler v0) if available
- validator report JSON (copyspace-validate --report report.json)

If schedule.json is too large:
- attach report.json and summary.json (if you used scripts/scheduler/stress_smoke.py)
- or attach a reduced instance that still reproduces the issue

## Environment
- OS:
- Python version:
- copy-space version (pip show copy-space) or git rev:
