#!/bin/sh
set -eu
scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_m_fastpath.f0 --dump-testg 52 --expect-hex 0100000024020000330000000000000008000000000000001234567889abcdefffffffff89abcdef8000000000000000fffffffe >/dev/null
echo "OK c3 m fastpath"
