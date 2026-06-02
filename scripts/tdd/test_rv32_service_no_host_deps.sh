#!/bin/sh
set -eu

# Ensure strict local-only execution: no network fetch/install tools in service gates.
# This protects "no external host-side dependencies" at test/runtime level.

if rg -n "curl|wget|git clone|pip install|apt-get|dnf install|npm install|go get|cargo install|http://|https://" \
  scripts/tdd \
  -g 'test_rv32_service_*.sh' \
  -g 'run_rv32_service_release.sh' \
  -g '!test_rv32_service_no_host_deps.sh' \
  >/dev/null; then
  echo "FAIL: host external dependency pattern found" >&2
  exit 1
fi

# Ensure local corpus exists and has binaries.
EXT="third_party/riscv-external"
[ -d "$EXT" ] || { echo "FAIL: missing $EXT" >&2; exit 1; }
find "$EXT" -name "*.bin" | head -n 1 >/dev/null

echo "OK rv32 service no host deps"
