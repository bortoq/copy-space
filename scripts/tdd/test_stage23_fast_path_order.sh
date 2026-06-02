#!/bin/sh
set -eu

# Fast-path order enforcement:
# if C3 lint is red, downstream stage23 policy/completion gates must stay red.

if bash scripts/tdd/test_rv32_c3_run_generator_lint.sh >/dev/null 2>&1; then
  echo "OK stage23 fast-path order (lint green)"
  exit 0
fi

bash scripts/tdd/test_rv32_stage23_policy_block.sh >/dev/null 2>&1 && {
  echo "FAIL: policy_block unexpectedly green while lint is red" >&2
  exit 1
}

bash scripts/tdd/test_rv32_stage23_completion_rule.sh >/dev/null 2>&1 && {
  echo "FAIL: completion_rule unexpectedly green while lint is red" >&2
  exit 1
}

echo "OK stage23 fast-path order"
