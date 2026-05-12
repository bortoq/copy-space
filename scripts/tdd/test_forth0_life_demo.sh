set -eu

test -x build/bin/mkimage_std7_fixed
test -x build/bin/forth0c
test -x build/bin/vmrun
test -x build/bin/vmprep_forth0

f0="src/forth0/demos/life.f0"
test -f "$f0"

scripts/forth0/run_f0.sh --in "$f0" --dump-testg 16 --expect-hex 00000038000000000000101010000000 >/dev/null
