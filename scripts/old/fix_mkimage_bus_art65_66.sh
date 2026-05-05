#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_fix_bus_art65_66"
mkdir -p "$bakdir"

F="src/mkimage/std7_fixed/legacy.c"
[ -f "$F" ] || { echo "FAIL: missing $F" >&2; exit 1; }
cp -a "$F" "$bakdir/legacy.c.bak"

# 1) ensure include devices.h
if grep -q '"devices.h"' "$F"; then
  echo "OK: legacy.c already includes devices.h"
else
  tmp="tmp/legacy_inc_${ts}.c"
  # insert after other std7_fixed includes; anchor on layout.h (present in your refactor)
  # if layout.h not found, insert after first include "words.h"
  if grep -q '"layout.h"' "$F"; then
    awk '
      BEGIN{done=0}
      {print}
      !done && $0 ~ /#include "layout\.h"/ {
        print "#include \"devices.h\""
        done=1
      }
      END{ if(!done) exit 2 }
    ' "$F" >"$tmp" || {
      echo "FAIL: cannot insert devices.h include (anchor layout.h missing/unexpected)" >&2
      exit 1
    }
  else
    awk '
      BEGIN{done=0}
      {print}
      !done && $0 ~ /#include "words\.h"/ {
        print "#include \"devices.h\""
        done=1
      }
      END{ if(!done) exit 2 }
    ' "$F" >"$tmp" || {
      echo "FAIL: cannot insert devices.h include (anchor words.h missing/unexpected)" >&2
      exit 1
    }
  fi
  mv "$tmp" "$F"
  echo "OK: inserted #include \"devices.h\""
fi

# 2) insert bus build block before std7_addrs_t A = {0};
if grep -q "std7_fixed_build_devices" "$F"; then
  echo "OK: legacy.c already calls std7_fixed_build_devices"
else
  tmp="tmp/legacy_bus_${ts}.c"
  awk '
    BEGIN{ins=0}
    {
      if (!ins && $0 ~ /std7_addrs_t[[:space:]]+A[[:space:]]*=[[:space:]]*\{0\}/) {
        print "  /* devices/bus: build TERM0 structures after pool (byte-aligned) */"
        print "  bitaddr_t pool_end_bits = POOL_BASE + (bitaddr_t)pool_cells * 64u;"
        print "  bitaddr_t BUS_GUARD_BITS = (bitaddr_t)64u * 8u;"
        print "  bitaddr_t BUS_SIZE_BITS  = (bitaddr_t)256u * 8u;"
        print "  bitaddr_t BUS_BASE = (pool_end_bits + BUS_GUARD_BITS + 7u) & ~(bitaddr_t)7u;"
        print "  if (BUS_BASE + BUS_SIZE_BITS + BUS_GUARD_BITS > TESTSCR_BASE) {"
        print "    fprintf(stderr, \"mkimage: BUS overlaps scratch\\n\");"
        print "    return 1;"
        print "  }"
        print "  std7_devices_t DEV = {0};"
        print "  if (std7_fixed_build_devices(&vm, BUS_BASE, &DEV) != 0) {"
        print "    fprintf(stderr, \"mkimage: std7_fixed_build_devices failed\\n\");"
        print "    return 1;"
        print "  }"
        print ""
        ins=1
      }
      print
    }
    END{ if(!ins) exit 2 }
  ' "$F" >"$tmp" || {
    echo "FAIL: cannot insert BUS build block (anchor std7_addrs_t A={0} not found)" >&2
    exit 1
  }
  mv "$tmp" "$F"
  echo "OK: inserted BUS build block"
fi

# 3) set A.bus_base and A.term0_desc before std7_fixed_write_artifacts
if grep -q "A.bus_base" "$F"; then
  echo "OK: legacy.c already assigns A.bus_base"
else
  tmp="tmp/legacy_A_bus_${ts}.c"
  awk '
    BEGIN{ins=0}
    {
      if (!ins && $0 ~ /std7_fixed_write_artifacts\(&vm,[[:space:]]*ART,[[:space:]]*&A\)/) {
        print "  /* devices/bus */"
        print "  A.bus_base   = BUS_BASE;"
        print "  A.term0_desc = DEV.term0_desc;"
        print ""
        ins=1
      }
      print
    }
    END{ if(!ins) exit 2 }
  ' "$F" >"$tmp" || {
    echo "FAIL: cannot insert A.bus_base assignments (anchor std7_fixed_write_artifacts call not found)" >&2
    exit 1
  }
  mv "$tmp" "$F"
  echo "OK: inserted A.bus_base / A.term0_desc assignments"
fi

echo "DONE: backup in $bakdir"
echo "Next: make test && make tdd"
