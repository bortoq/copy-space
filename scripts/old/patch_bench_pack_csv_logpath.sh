#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_patch_bench_pack_csv_logpath"
mkdir -p "$bakdir"

F="scripts/bench_pack_csv.sh"
[ -f "$F" ] || { echo "FAIL: missing $F" >&2; exit 1; }

cp -a "$F" "$bakdir/bench_pack_csv.sh.bak"

# If already patched (has BENCH_LOG), do nothing
if grep -q 'BENCH_LOG=' "$F"; then
  echo "OK: already patched: $F" >&2
  exit 0
fi

tmp="tmp/bench_pack_csv_patch_${ts}.sh"
mkdir -p tmp

awk '
BEGIN{done=0}
{
  print

  # Insert right after the bench run line
  if (!done && $0 ~ /^sh[[:space:]]+scripts\/bench_pack\.sh[[:space:]]*$/) {
    print ""
    print "# pick log that contains [vmrep]..VMREP_END"
    print "BENCH_LOG=\"${BENCH_LOG:-tmp/bench_pack.log}\""
    print "if [ ! -f \"$BENCH_LOG\" ]; then"
    print "  if [ -f tmp/bench_pack.log ]; then BENCH_LOG=tmp/bench_pack.log;"
    print "  elif [ -f tmp/mkbench_pack.log ]; then BENCH_LOG=tmp/mkbench_pack.log;"
    print "  else"
    print "    echo \"FAIL: cannot find bench log (tmp/bench_pack.log or tmp/mkbench_pack.log)\" >&2"
    print "    ls -la tmp >&2 || true"
    print "    exit 1"
    print "  fi"
    print "fi"
    print ""
    done=1
  }
}
END{ if(!done) exit 2 }
' "$F" >"$tmp" || { echo "FAIL: cannot patch $F (anchor: sh scripts/bench_pack.sh)" >&2; exit 1; }

mv "$tmp" "$F"
chmod +x "$F"

# Now patch the --log argument from tmp/run.log to "$BENCH_LOG"
# (safe: only touches this script)
# use python to avoid sed -i portability issues
python3 - <<'PY'
from pathlib import Path
p = Path("scripts/bench_pack_csv.sh")
t = p.read_text(encoding="utf-8", errors="replace")
t2 = t.replace("--log tmp/run.log", '--log "$BENCH_LOG"')
p.write_text(t2, encoding="utf-8")
print("OK: updated --log to use $BENCH_LOG")
PY

echo "OK: patched $F (backup: $bakdir/bench_pack_csv.sh.bak)" >&2
