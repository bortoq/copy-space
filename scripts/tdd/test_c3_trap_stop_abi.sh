#!/bin/sh
set -eu

run_case() {
  name="$1"
  in_f0="$2"
  exp_reason="$3"
  tmp="tmp/c3_trap_abi/$name"
  scripts/forth0/run_f0.sh --in "$in_f0" --dump-testg 20 --keep --tmpdir "$tmp" >/dev/null
  test -f "$tmp/testg.bin"
  python3 scripts/riscv/c3_stop_dump_check.py --bin "$tmp/testg.bin" --expect-reason "$exp_reason" >/dev/null
}

run_case illegal src/forth0/tests/test_c3_m0_stop_contract.f0 3
run_case mem_align src/forth0/tests/test_c3_mem_align_fault.f0 4
run_case mem_bounds src/forth0/tests/test_c3_mem_bounds_fault.f0 4
run_case arith src/forth0/tests/test_c3_arith_fault.f0 5

echo "OK c3 trap stop ABI"
