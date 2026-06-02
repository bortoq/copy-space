#!/bin/sh
set -eu
scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_m_div4.f0 --dump-testg 52 --expect-hex 010000001002004033000000000000000800000000000000000000001234567812345678ffffffffffffffff89abcdef89abcdef >/dev/null
echo "OK c3 m div4"
