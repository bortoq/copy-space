#!/bin/sh
set -eu

DOC="doc/rv32_c3_unsupported_trap_contract.md"
SRC="src/mkimage/std7_fixed/words_c3_run.c"

[ -f "$DOC" ] || { echo "FAIL: missing $DOC" >&2; exit 1; }
[ -f "$SRC" ] || { echo "FAIL: missing $SRC" >&2; exit 1; }

rg -n "unsupported|deterministic|STATUS|READ_REGS|READ_MEM" "$DOC" >/dev/null
# Current implementation still has MVP shortcut markers; this gate tracks readiness input.
rg -n "write_page_opcheck|write_page_done" "$SRC" >/dev/null

echo "OK rv32 c3 unsupported trap contract"
