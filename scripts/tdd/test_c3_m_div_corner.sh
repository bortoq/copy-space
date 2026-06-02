#!/bin/sh
set -eu
scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_m_div_corner.f0 --dump-testg 52 --expect-hex 0100000010020040330000000000000008000000800000000000000000000000ffffffff7fffffff00000001ffffffff12345678 >/dev/null
echo "OK c3 m div corner"
