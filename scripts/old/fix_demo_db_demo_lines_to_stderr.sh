cat > scripts/fix_demo_db_demo_lines_to_stderr.sh <<'EOF'
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
import re

p = Path("scripts/demo_db.sh")
lines = p.read_text(encoding="utf-8", errors="replace").splitlines(True)

changed = 0
out = []

# match lines that look like: echo "...[demo]..."   OR   printf "...[demo]..."
pat = re.compile(r'^\s*(echo|printf)\b.*\[demo\].*')

for ln in lines:
    if pat.match(ln) and ('>&2' not in ln) and ('1>&2' not in ln):
        # Add stderr redirect at end of the command line.
        # Keep newline.
        if ln.endswith("\n"):
            ln2 = ln[:-1] + " >&2\n"
        else:
            ln2 = ln + " >&2"
        out.append(ln2)
        changed += 1
    else:
        out.append(ln)

p.write_text("".join(out), encoding="utf-8")
print(f"OK: patched {p} (demo lines redirected to stderr: {changed})")
PY

chmod +x "$F"
EOF

chmod +x scripts/fix_demo_db_demo_lines_to_stderr.sh
sh scripts/fix_demo_db_demo_lines_to_stderr.sh
