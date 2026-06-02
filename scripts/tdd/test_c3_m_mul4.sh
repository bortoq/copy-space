#!/bin/sh
set -eu
scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_m_mul4.f0 --dump-testg 52 --expect-hex 0100000010020010330000000000000008000000242d2080f8cc93d60b00ea4e0b00ea4efffffffeffffffff00000001ffffffff >/dev/null
echo "OK c3 m mul4"
