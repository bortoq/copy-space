#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_patch_bench_pack_csv_autobins"
mkdir -p "$bakdir"

F="scripts/bench_pack_csv.sh"
[ -f "$F" ] || { echo "FAIL: missing $F" >&2; exit 1; }

cp -a "$F" "$bakdir/bench_pack_csv.sh.bak"

# If already patched, do nothing
if grep -q "ensure tools exist" "$F"; then
  echo "OK: already patched: $F" >&2
  exit 0
fi

tmp="tmp/bench_pack_csv_${ts}.sh"
mkdir -p tmp

awk '
BEGIN{done=0}
{
  if (!done && $0 ~ /^sh[[:space:]]+scripts\/bench_pack\.sh/) {
    print ""
    print "# ensure tools exist"
    print "if [ ! -x build/bin/mkimage_std7_fixed ]; then"
    print "  make bins"
    print "fi"
    print ""
    done=1
  }
  print
}
END{ if(!done) exit 2 }
' "$F" >"$tmp" || { echo "FAIL: cannot patch (anchor: sh scripts/bench_pack.sh not found)" >&2; exit 1; }

mv "$tmp" "$F"
chmod +x "$F"
echo "OK: patched $F (backup: $bakdir/bench_pack_csv.sh.bak)" >&2
