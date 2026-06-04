#!/bin/sh
set -eu

GEN="scripts/riscv/gen_c3_run.py"
OUT="src/mkimage/std7_fixed/words_c3_run.c"

[ -f "$GEN" ] || { echo "FAIL: missing $GEN" >&2; exit 1; }
[ -f "$OUT" ] || { echo "FAIL: missing $OUT" >&2; exit 1; }

# Patchable slot fields inside generated pages must target live processor slots.
# The currently executing layer lives at processor_start=0, so self-patching
# must use absolute slot addresses, not backing-image-relative img addresses.
if rg -n "bitaddr_t (slot2_src|chain_src|slot_addr) = img \\+" "$OUT" >/dev/null 2>&1; then
  echo "FAIL: generated C3_RUN still patches backing image instead of live processor slots" >&2
  exit 1
fi

rg -n "bitaddr_t slot2_src = 0 \\+" "$OUT" >/dev/null
rg -n "bitaddr_t chain_src = vm_proc_slot_field_ip\\(vm, last, vm->off_src\\)" "$OUT" >/dev/null

echo "OK rv32 c3 relative patch contract"
