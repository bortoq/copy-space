#!/bin/sh
set -eu

# Stage-20 replacement gate:
# verify loader/runtime handoff, slice independence and channel IO path.
sh scripts/tdd/test_rv32m_slice_independence.sh >/dev/null
sh scripts/tdd/test_rv32m_unified_entrypoint.sh >/dev/null
sh scripts/tdd/test_rv32m_channel_io_roundtrip.sh >/dev/null

echo "OK rv32 service ext lw/sw (in-space replacement)"
