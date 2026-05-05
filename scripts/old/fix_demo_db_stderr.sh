#!/bin/sh
set -eu
ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_fix_demo_db_stderr"
mkdir -p "$bakdir"

F="scripts/demo_db.sh"
[ -f "$F" ] || { echo "FAIL: missing $F" >&2; exit 1; }
cp -a "$F" "$bakdir/demo_db.sh.bak"

python3 - <<'PY'
from pathlib import Path
p = Path("scripts/demo_db.sh")
lines = p.read_text(encoding="utf-8", errors="replace").splitlines(True)
out=[]
for ln in lines:
    if 'printf "%s\\n" "[demo]' in ln and '>&2' not in ln:
        # add stderr redirect before newline
        if ln.endswith("\n"):
            ln = ln[:-1] + " >&2\n"
        else:
            ln = ln + " >&2"
    out.append(ln)
p.write_text("".join(out), encoding="utf-8")
print("OK: updated demo to print [demo] lines to stderr")
PY

chmod +x "$F"
echo "OK: patched $F (backup: $bakdir/demo_db.sh.bak)" >&2
