#!/bin/sh
set -eu

DOC="doc/c3_run_shortcuts_inventory.md"
SRC="src/mkimage/std7_fixed/words_c3_run.c"

[ -f "$DOC" ] || { echo "FAIL: missing $DOC" >&2; exit 1; }
[ -f "$SRC" ] || { echo "FAIL: missing $SRC" >&2; exit 1; }

# Inventory must reference concrete known MVP markers from implementation.
rg -n "For MVP \(rd=1\)|skip full increment|write_page_budget|opcode" "$DOC" >/dev/null
rg -n "For MVP \(rd=1\)|skip full increment|write_page_budget|write_page_opcheck" "$SRC" >/dev/null

echo "OK rv32 c3_run shortcuts inventory"
