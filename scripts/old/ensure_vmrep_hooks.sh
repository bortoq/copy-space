#!/bin/sh
set -eu

F="src/vm/space.c"
test -f "$F"

python3 - <<'PY'
from pathlib import Path
import re, sys

p = Path("src/vm/space.c")
s = p.read_text(encoding="utf-8", errors="replace")

if "VMREP_BEGIN" not in s:
    print("ERROR: VMREP block not found in src/vm/space.c (VMREP_BEGIN missing).", file=sys.stderr)
    print("       Apply vmrep block first, then re-run this script.", file=sys.stderr)
    sys.exit(2)

# Locate vm_tick body (simple regex; relies on your current formatting)
m = re.search(r'vm_rc_t\s+vm_tick\s*\(\s*vm_t\s*\*\s*vm\s*,\s*FILE\s*\*\s*in\s*,\s*FILE\s*\*\s*out\s*\)\s*\{', s)
if not m:
    print("ERROR: vm_tick signature not found", file=sys.stderr)
    sys.exit(3)

start = m.end()
# find end of function by counting braces from first '{'
i = m.start()
open_brace = s.find("{", i)
if open_brace < 0: raise SystemExit("no {")
depth = 0
j = open_brace
while j < len(s):
    if s[j] == "{": depth += 1
    elif s[j] == "}":
        depth -= 1
        if depth == 0:
            end = j
            break
    j += 1
else:
    raise SystemExit("no matching } for vm_tick")

tick = s[open_brace+1:end]

# 1) Ensure vmrep_tick_begin(vm->processor_n); after "/* 3) fetch-execute slots */"
anchor3 = "  /* 3) fetch-execute slots */\n"
idx = tick.find(anchor3)
if idx < 0:
    print("ERROR: cannot find anchor comment '/* 3) fetch-execute slots */' in vm_tick", file=sys.stderr)
    sys.exit(4)

insert_pos = idx + len(anchor3)
if "vmrep_tick_begin" not in tick[insert_pos:insert_pos+200]:
    tick = tick[:insert_pos] + "\n  vmrep_tick_begin(vm->processor_n);\n" + tick[insert_pos:]

# 2) Ensure vmrep_note_copy(...) immediately before bitcpy(...) call
# Your canonical line:
# bitcpy((size_t)n, vm->space, (size_t)src, vm->space, (size_t)dst);
bitcpy_pat = r'(\n\s*)bitcpy\(\(size_t\)n,\s*vm->space,\s*\(size_t\)src,\s*vm->space,\s*\(size_t\)dst\);\s*'
m2 = re.search(bitcpy_pat, tick)
if not m2:
    print("ERROR: cannot find canonical bitcpy((size_t)n, vm->space, (size_t)src, vm->space, (size_t)dst); in vm_tick", file=sys.stderr)
    sys.exit(5)

before = tick[:m2.start()]
call = tick[m2.start():m2.end()]
after = tick[m2.end():]

if "vmrep_note_copy" not in before[-200:]:
    note = f"{m2.group(1)}vmrep_note_copy((uint64_t)dst, (uint64_t)n);\n"
    tick = before + note + call + after

# 3) Ensure vmrep_tick_end(); before 'return VM_OK;'
ret_pat = r'\n(\s*)return\s+VM_OK\s*;\s*'
m3 = re.search(ret_pat, tick)
if not m3:
    print("ERROR: cannot find 'return VM_OK;' in vm_tick body", file=sys.stderr)
    sys.exit(6)

# check if tick_end already near return
near = tick[max(0, m3.start()-200):m3.start()]
if "vmrep_tick_end" not in near:
    tick = tick[:m3.start()] + f"\n{m3.group(1)}vmrep_tick_end();\n" + tick[m3.start():]

# Reassemble
s2 = s[:open_brace+1] + tick + s[end:]

if s2 == s:
    print("INFO: no changes needed (hooks already present).")
else:
    p.write_text(s2, encoding="utf-8")
    print("OK: ensured vmrep hooks in vm_tick().")
PY