#!/bin/sh
set -eu

# compile vm core users to ensure new MMIO fields/protocol are wired
make bins >/dev/null

# smoke: existing vmrun path should still work
scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_layout.f0 --dump-testg 20 >/dev/null

echo "OK vm loader/channel/watchdog mmio smoke"
